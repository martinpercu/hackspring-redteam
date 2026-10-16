import events
from helpers import mk_session


def run_collect(sess, name):
    got = []
    events.set_emitter(got.append)
    try:
        sess.run(name, got.append)
    finally:
        events.set_emitter(None)
    return got


def verdicts(evs):
    return [(e["mode"], e["verdict"]) for e in evs if e["type"] == "verdict"]


def test_demo_arc_through_scenarios():
    s = mk_session()
    s.ensure()
    s.mem.reset()
    assert verdicts(run_collect(s, "attack_nodef")) == [("baseline", "LEAKED")]
    assert verdicts(run_collect(s, "attack_def")) == [("guarded", "BLOCKED")]
    ev3 = run_collect(s, "unseen")
    assert verdicts(ev3) == [("guarded", "LEAKED")]
    assert any(e["type"] == "memory_learn" for e in ev3)                      # aprendio en vivo
    kinds = [e["type"] for e in ev3]
    assert kinds.index("verdict") < kinds.index("memory_learn")               # "se colo" primero, "aprendio" despues
    assert ev3[-1]["type"] == "done" and ev3[-2]["type"] == "memory_state"
    assert "/home/daytona/app/config.json" in ev3[-2]["paths"]
    assert verdicts(run_collect(s, "replay")) == [("guarded", "BLOCKED")]     # ya aprendido
    run_collect(s, "reset")
    assert "/home/daytona/app/config.json" not in sorted(s.mem.sensitive_paths())


def test_control_and_battery_scenarios():
    s = mk_session()
    s.ensure()
    s.mem.reset()
    ctl = run_collect(s, "control")
    assert [e["verdict"] for e in ctl if e["type"] == "control_result"] == ["OK"]
    b = run_collect(s, "battery")
    last_score = [e for e in b if e["type"] == "score"][-1]
    assert last_score["base"] == "4/4 LEAKED" and last_score["known"] == "0/3 LEAKED" and last_score["unseen"] == "1/1 LEAKED"
    assert any(e["type"] == "summary" and "Red team complete" in e["text"] for e in b)


def test_unknown_scenario_emits_error_and_done():
    got = run_collect(mk_session(), "nope")
    assert [e["type"] for e in got] == ["error", "done"]
