import json
import os
import tempfile
import threading
import urllib.error
import urllib.request

import dashboard as D
from helpers import mk_session
from narrator import Narrator
from scenarios import SCENARIOS


def sse(url):
    evs = []
    with urllib.request.urlopen(url, timeout=20) as r:
        for line in r:
            line = line.decode().strip()
            if line.startswith("data: "):
                evs.append(json.loads(line[6:]))
                if evs[-1]["type"] == "done":
                    break
    return evs


def test_http_server_sse_live_then_playback():
    rec_dir = tempfile.mkdtemp()
    web = tempfile.mkdtemp()
    open(os.path.join(web, "index.html"), "w").write("<html>AGENT RED TEAM</html>")
    os.makedirs(os.path.join(web, "audio"))
    open(os.path.join(web, "audio", "a.mp3"), "wb").write(b"ID3")
    sess = mk_session()
    narrator = Narrator(lambda text, who: "/audio/a.mp3")
    app = D.App(sess.run, SCENARIOS, narrator, web_dir=web, recordings_dir=rec_dir)
    srv = D.make_server(app, 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    try:
        assert b"AGENT RED TEAM" in urllib.request.urlopen(base + "/").read()
        assert urllib.request.urlopen(base + "/healthz").read() == b"ok"
        assert urllib.request.urlopen(base + "/audio/a.mp3").read() == b"ID3"
        assert json.load(urllib.request.urlopen(base + "/api/state"))["offline"] == []
        live = sse(base + "/scenario/attack_nodef")
        assert live[-1]["type"] == "done"
        assert ("baseline", "LEAKED") in [(e["mode"], e["verdict"]) for e in live if e["type"] == "verdict"]
        assert any(e["type"] == "say" and e["audio"] == "/audio/a.mp3" for e in live)     # narracion en el stream
        assert json.load(urllib.request.urlopen(base + "/api/state"))["offline"] == ["attack_nodef"]  # se grabo
        play = sse(base + "/playback/attack_nodef")                                       # sin tocar el motor
        assert [e["type"] for e in play] == [e["type"] for e in live]
        for bad in ("/scenario/nope", "/nope", "/audio/../../etc/passwd"):
            try:
                urllib.request.urlopen(base + bad)
                raise AssertionError(f"deberia fallar: {bad}")
            except urllib.error.HTTPError as e:
                assert e.code == 404
        miss = sse(base + "/playback/battery")                                            # sin grabacion -> error + done
        assert [e["type"] for e in miss] == ["error", "done"]
    finally:
        srv.shutdown()
