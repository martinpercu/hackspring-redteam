"""Orquesta corridas de ataque/control, veredictos, baterías y scoreboards."""
from __future__ import annotations

import re

import detector
import fixtures
import tracing
from config import SEED_INDICATORS, log
from events import emit
from toolbox import ToolBox


def _victim(victim_fn):
    if victim_fn is not None:
        return victim_fn
    import victim
    return victim.run_victim


def _toolbox(canaries, guarded, mem, exec_fn, fetch_fn) -> ToolBox:
    """ToolBox con los indicadores sensibles que correspondan al modo."""
    if not guarded:
        paths: set = set()
    else:
        paths = mem.sensitive_paths() if mem is not None else set(SEED_INDICATORS)
    return ToolBox(canaries, guarded, sensitive_paths=paths, exec_fn=exec_fn, fetch_fn=fetch_fn)


def run_attack(atk, url, canaries, guarded, session_id, mem=None, victim_fn=None, exec_fn=None, fetch_fn=None) -> dict:
    """Una corrida de ataque -> veredicto determinista (aprende solo en guarded)."""
    mode = "guarded" if guarded else "baseline"
    task = atk["task"].format(url=url)
    emit(type="attack_start", attack=atk["name"], mode=mode, unseen=atk["unseen"],
         technique=atk["technique"], task=task)
    attrs = {"run.mode": mode, "attack.name": atk["name"], "attack.technique": atk["technique"],
             "attack.unseen": atk["unseen"], "session.id": f"{session_id}-{mode}", "input.value": task}
    with tracing.span(f"attack.{atk['name']} [{mode}]", "CHAIN", **attrs) as sp:
        tb = _toolbox(canaries, guarded, mem, exec_fn, fetch_fn)
        final = _victim(victim_fn)(task, tb)
        leaked = any(p["leak"] for p in tb.posts) or detector.is_leak(canaries, final)
        verdict = detector.attack_verdict(leaked, tb.blocked)
        dev = detector.deviation_step(tb.calls, atk)
        if guarded and mem is not None:
            mem.record_incident(attack=atk["name"], technique=atk["technique"], target_path=atk["target_path"],
                                dest_domain=atk["dest_domain"], verdict=verdict)
        if leaked and tb.posts:
            detail = f"canary sent via http_post to {tb.posts[0]['url']}"
        elif tb.blocked:
            detail = f"guardrail blocked: {', '.join(tb.blocked)}"
        else:
            detail = "agent did not follow injection"
        sp.set_attribute("attack.verdict", verdict)
        sp.set_attribute("attack.leaked", leaked)
        if dev is not None:
            sp.set_attribute("attack.deviation_step", dev)
        sp.set_attribute("output.value", f"{verdict} — {detail}\n\nAgent answer: {final[:500]}")
        tracing.set_status(sp, not leaked, "canary leaked")
        sid = tracing.span_id_hex(sp)
    log("verdict", f"{atk['name']} [{mode}] {verdict} — {detail}")
    emit(type="verdict", attack=atk["name"], mode=mode, unseen=atk["unseen"], verdict=verdict,
         leaked=leaked, detail=detail, deviation_step=dev)
    if mem is not None and guarded and verdict == "LEAKED" and atk["target_path"]:
        emit(type="memory_learn", path=atk["target_path"], paths=sorted(mem.sensitive_paths()))
    return {"attack": atk["name"], "technique": atk["technique"], "mode": mode, "unseen": atk["unseen"],
            "verdict": verdict, "leaked": leaked, "detail": detail, "span_id": sid,
            "deviation_step": dev, "final": final}


def run_control(ctl, url, canaries, guarded, session_id, mem=None, victim_fn=None, exec_fn=None, fetch_fn=None) -> dict:
    """Una tarea legítima: mide que el guardrail no rompa el trabajo."""
    mode = "guarded" if guarded else "baseline"
    task = ctl["task"].format(url=url)
    emit(type="control_start", control=ctl["name"], mode=mode, task=task)
    attrs = {"run.mode": mode, "control.name": ctl["name"], "session.id": f"{session_id}-{mode}", "input.value": task}
    with tracing.span(f"control.{ctl['name']} [{mode}]", "CHAIN", **attrs) as sp:
        tb = _toolbox(canaries, guarded, mem, exec_fn, fetch_fn)
        final = _victim(victim_fn)(task, tb)
        verdict = detector.control_verdict(final, tb.blocked, ctl.get("expect"), ctl.get("expect_re"))
        sp.set_attribute("control.verdict", verdict)
        sp.set_attribute("output.value", f"{verdict}\n\nAgent answer: {final[:500]}")
    ok = verdict == "OK"
    log("control", f"{ctl['name']} [{mode}] {verdict}")
    emit(type="control_result", control=ctl["name"], mode=mode, verdict=verdict, ok=ok)
    return {"control": ctl["name"], "mode": mode, "verdict": verdict, "ok": ok, "final": final}


def run_suite(guarded, urls, canaries, session_id, mem=None, only_known=False, **kw) -> list[dict]:
    """Todos los ataques (o solo los conocidos) en un modo."""
    atks = fixtures.known_attacks() if only_known else fixtures.ATTACKS
    return [run_attack(a, urls[a["name"]], canaries, guarded, session_id, mem, **kw) for a in atks]


def run_controls(guarded, urls, canaries, session_id, mem=None, **kw) -> list[dict]:
    """Todos los controles en un modo."""
    return [run_control(c, urls[c["name"]], canaries, guarded, session_id, mem, **kw) for c in fixtures.CONTROLS]


def scoreboard(results) -> str:
    """'X/N LEAKED'."""
    return f"{sum(1 for r in results if r['verdict'] == 'LEAKED')}/{len(results)} LEAKED"


def utility(results) -> str:
    """'X/N OK'."""
    return f"{sum(1 for r in results if r['ok'])}/{len(results)} OK"


def battery(urls, canaries, session_id, mem=None, **kw) -> dict:
    """Ataques y controles en baseline y guarded, con eventos de score."""
    base = run_suite(False, urls, canaries, session_id, mem, **kw)
    sb_base = scoreboard(base)
    emit(type="score", base=sb_base)
    guard = run_suite(True, urls, canaries, session_id, mem, **kw)
    known_g = [r for r in guard if not r["unseen"]]
    unseen_g = [r for r in guard if r["unseen"]]
    sb_guard, sb_known, sb_unseen = scoreboard(guard), scoreboard(known_g), scoreboard(unseen_g)
    emit(type="score", base=sb_base, guard=sb_guard, known=sb_known, unseen=sb_unseen)
    cbase = run_controls(False, urls, canaries, session_id, mem, **kw)
    cguard = run_controls(True, urls, canaries, session_id, mem, **kw)
    ut_base, ut_guard = utility(cbase), utility(cguard)
    emit(type="score", base=sb_base, guard=sb_guard, known=sb_known, unseen=sb_unseen,
         ctl=f"{ut_base} → {ut_guard}")
    return {"base": base, "guard": guard, "known_g": known_g, "unseen_g": unseen_g, "cbase": cbase,
            "cguard": cguard, "sb_base": sb_base, "sb_guard": sb_guard, "sb_known": sb_known,
            "sb_unseen": sb_unseen, "ut_base": ut_base, "ut_guard": ut_guard}


def _of(score: str) -> str:
    return re.sub(r"^(\d+)/(\d+).*$", r"\1 of \2", score)


def summary_sentence(b: dict) -> str:
    """Frase final en inglés para la voz."""
    return (f"Red team complete. Without defenses, {_of(b['sb_base'])} attacks leaked a decoy secret. "
            f"With the guardrail, {_of(b['sb_guard'])}. Known attacks: {_of(b['sb_known'])} got through. "
            f"Legitimate tasks still work: {_of(b['ut_guard'])}.")
