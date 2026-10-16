import json
import os
import tempfile

import replay
from narrator import LINES, Narrator, line_key


def test_recorder_roundtrip_and_find():
    d = tempfile.mkdtemp()
    rec = replay.Recorder(d)
    rec.start()
    rec.add({"type": "attack_start"})
    rec.add({"type": "done"})
    p = rec.save("battery")
    assert os.path.exists(p) and [i["ev"]["type"] for i in replay.load(p)] == ["attack_start", "done"]
    assert replay.find_recording(d, "battery") == p                # sin demo/ -> usa last/
    assert replay.find_recording(d, "nope") is None
    assert replay.freeze(d) == ["battery.json"]
    assert replay.find_recording(d, "battery").endswith(os.path.join("demo", "battery.json"))   # demo/ gana


def test_replay_caps_long_gaps():
    import time
    got = []
    t0 = time.time()
    replay.replay([{"t": 0, "ev": {"type": "a"}}, {"t": 60, "ev": {"type": "done"}}], got.append, max_gap=0.05)
    assert [e["type"] for e in got] == ["a", "done"] and time.time() - t0 < 1


def test_line_keys():
    assert line_key({"type": "attack_start", "mode": "baseline"}) == "intro_known"
    assert line_key({"type": "attack_start", "mode": "guarded", "unseen": False}) == "intro_guarded"
    assert line_key({"type": "attack_start", "mode": "guarded", "unseen": True}) == "intro_unseen"
    assert line_key({"type": "verdict", "mode": "baseline", "verdict": "LEAKED"}) == "leaked"
    assert line_key({"type": "verdict", "mode": "guarded", "verdict": "LEAKED"}) == "leaked_unseen"
    assert line_key({"type": "verdict", "mode": "guarded", "verdict": "BLOCKED"}) == "blocked"
    assert line_key({"type": "verdict", "mode": "guarded", "unseen": True, "verdict": "BLOCKED"}) == "blocked_learned"
    assert line_key({"type": "verdict", "mode": "guarded", "verdict": "SAFE"}) == "safe"
    assert line_key({"type": "memory_learn"}) == "learned"
    assert line_key({"type": "tool"}) is None
    assert all(who in ("attacker", "defender") and text for who, text in LINES.values())


def test_narrator_adds_say_events_and_survives_voice_failure():
    out = []
    n = Narrator(lambda text, who: f"/audio/{who}.mp3")
    f = n.wrap(out.append)
    f({"type": "verdict", "mode": "baseline", "verdict": "LEAKED"})
    f({"type": "tool"})
    f({"type": "summary", "text": "Red team complete."})
    assert [e["type"] for e in out] == ["verdict", "say", "tool", "summary", "say"]
    assert out[1]["who"] == "attacker" and out[1]["audio"] == "/audio/attacker.mp3"
    assert out[-1]["text"] == "Red team complete."

    def boom(text, who):
        raise RuntimeError("no network")
    out2 = []
    Narrator(boom).wrap(out2.append)({"type": "memory_learn"})
    assert out2[-1]["type"] == "say" and out2[-1]["audio"] is None      # sigue sin voz

    out4 = []                                   # durante `battery` solo se narra el resumen final
    f4 = Narrator(lambda t, w: "/audio/x.mp3").wrap(out4.append)
    f4({"type": "scenario_start", "scenario": "battery"})
    f4({"type": "verdict", "mode": "baseline", "verdict": "LEAKED"})
    f4({"type": "memory_learn"})
    f4({"type": "summary", "text": "Done."})
    assert [e["type"] for e in out4] == ["scenario_start", "verdict", "memory_learn", "summary", "say"]
    f4({"type": "scenario_start", "scenario": "attack_nodef"})      # el siguiente escenario vuelve a narrar
    f4({"type": "verdict", "mode": "baseline", "verdict": "LEAKED"})
    assert out4[-1]["type"] == "say"

    out5 = []                                   # replay = 2do intento del no visto: intro propia
    f5 = Narrator(lambda t, w: "/audio/x.mp3").wrap(out5.append)
    f5({"type": "scenario_start", "scenario": "replay"})
    f5({"type": "attack_start", "mode": "guarded", "unseen": True})
    assert out5[-1]["text"] == LINES["intro_replay"][1]
    f5({"type": "scenario_start", "scenario": "unseen"})
    f5({"type": "attack_start", "mode": "guarded", "unseen": True})
    assert out5[-1]["text"] == LINES["intro_unseen"][1]

    out3 = []
    Narrator(lambda t, w: "x", enabled=False).wrap(out3.append)({"type": "memory_learn"})
    assert len(out3) == 1                                                # voz apagada -> sin `say`


def test_voice_narrate_cache_and_no_key():
    import voice
    d = tempfile.mkdtemp()
    os.environ.pop("ELEVENLABS_API_KEY", None)
    assert voice.narrate("hello", "defender", audio_dir=d) is None       # sin key y sin cache -> None
    open(os.path.join(d, voice.audio_name("hello", "defender")), "wb").write(b"mp3")
    assert voice.narrate("hello", "defender", audio_dir=d) == "/audio/" + voice.audio_name("hello", "defender")
    assert voice.audio_name("hello", "defender") != voice.audio_name("hello", "attacker")
    assert voice.speak("x", os.path.join(d, "s.mp3")) is None            # sin key -> None, no explota
