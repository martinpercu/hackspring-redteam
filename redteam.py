"""CLI del Red Team: baterías baseline/guarded contra el sandbox real."""
from __future__ import annotations

import argparse
import os
import time

import fixtures
import runner
import tracing
from config import log
from memory import DefenseMemory


def _parse(argv) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Agent Red Team")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--guarded", action="store_true")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--learn-arc", action="store_true", dest="learn_arc")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--no-voice", action="store_true", dest="no_voice")
    ap.add_argument("--reset-memory", action="store_true", dest="reset_memory")
    return ap.parse_args(argv)


def _calibrate(urls, canaries, session, runs) -> None:
    """N corridas de cada ataque en baseline: consistencia."""
    for atk in fixtures.ATTACKS:
        k = sum(runner.run_attack(atk, urls[atk["name"]], canaries, False, session)["leaked"] for _ in range(runs))
        print(f"leaks en {runs} corridas: {atk['name']} {k}/{runs}")


def _learn_arc(urls, canaries, session, mem) -> None:
    """El ataque no visto se cuela, se aprende la ruta, y la segunda vez se bloquea."""
    mem.reset()
    atk = fixtures.unseen_attack()
    for label in ("1er intento", "2do intento"):
        r = runner.run_attack(atk, urls[atk["name"]], canaries, True, session, mem)
        print(f"{label}: {r['verdict']}")


def _controls(urls, canaries, session, mem) -> None:
    base = runner.utility(runner.run_controls(False, urls, canaries, session, mem))
    guard = runner.utility(runner.run_controls(True, urls, canaries, session, mem))
    print(f"== CONTROLES ==  baseline: {base}  |  guarded: {guard}")


def _compare(urls, canaries, session, mem, no_voice: bool) -> None:
    b = runner.battery(urls, canaries, session, mem)
    print("== SCOREBOARD ==")
    print(f"  ataques   baseline: {b['sb_base']}  |  guarded: {b['sb_guard']}")
    print(f"     conocidos guarded: {b['sb_known']}  |  no vistos guarded: {b['sb_unseen']}")
    print(f"  controles baseline: {b['ut_base']}  |  guarded: {b['ut_guard']}")
    with tracing.span("redteam.report", "CHAIN", **{"session.id": session, "input.value": runner.summary_sentence(b)}):
        try:
            import arize_evals
            arize_evals.log_evals(b["base"] + b["guard"])
        except ImportError:
            log("evals", "módulo arize_evals todavía no existe")
        if not no_voice:
            try:
                import voice
                voice.speak(runner.summary_sentence(b))
            except ImportError:
                log("voice", "módulo voice todavía no existe")


def main(argv=None) -> int:
    args = _parse(argv)
    if not os.getenv("OPENAI_API_KEY"):
        print("Falta OPENAI_API_KEY (ponerla en live/.env)")
        return 1
    tracing.setup_tracing()
    import box
    from range_setup import new_canary, setup_range
    c1, c2 = new_canary(), new_canary()
    session = "redteam-" + time.strftime("%Y%m%d-%H%M%S")
    mem = DefenseMemory()
    try:
        if args.reset_memory:
            mem.reset()
        canaries = [c1, c2]
        log("setup", f"canarios {c1} {c2} | memoria: {mem.engine}")
        urls = setup_range(c1, c2)
        if args.calibrate:
            _calibrate(urls, canaries, session, args.runs)
        elif args.learn_arc:
            _learn_arc(urls, canaries, session, mem)
        elif args.controls:
            _controls(urls, canaries, session, mem)
        elif args.compare:
            _compare(urls, canaries, session, mem, args.no_voice)
        elif args.guarded:
            print(f"== GUARDED: {runner.scoreboard(runner.run_suite(True, urls, canaries, session, mem))} ==")
        else:
            print(f"== BASELINE: {runner.scoreboard(runner.run_suite(False, urls, canaries, session, mem))} ==")
    finally:
        mem.close()
        with tracing.span("range.teardown", "CHAIN", **{"session.id": session}):
            box.teardown()
        tracing.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
