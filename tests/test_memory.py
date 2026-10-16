from config import SEED_INDICATORS
from memory import DefenseMemory


def fresh():
    m = DefenseMemory()
    m.reset()
    return m


def test_engine_is_up():
    m = DefenseMemory()
    assert not m.engine.startswith("fallback"), f"SurrealDB no levanto: {m.engine}"


def test_seed_and_learn():
    m = fresh()
    assert m.sensitive_paths() == set(SEED_INDICATORS)
    m.record_incident(attack="gist-exfil", technique="t", target_path="/home/daytona/app/config.json",
                      dest_domain="api.github.com", verdict="LEAKED")
    assert "/home/daytona/app/config.json" in m.sensitive_paths()
    assert m.incident_count() == 1


def test_blocked_does_not_learn_but_logs():
    m = fresh()
    m.record_incident(attack="a", technique="t", target_path="/x/y", dest_domain="d", verdict="BLOCKED")
    assert m.sensitive_paths() == set(SEED_INDICATORS)
    assert m.incident_count() == 1


def test_learn_is_idempotent_and_reset_forgets():
    m = fresh()
    for _ in range(3):
        m.record_incident(attack="a", technique="t", target_path="/x/y.json", dest_domain="d", verdict="LEAKED")
    assert len([r for r in m.learned_rows() if r["value"] == "/x/y.json"]) == 1
    m.reset()
    assert m.sensitive_paths() == set(SEED_INDICATORS) and m.incident_count() == 0
