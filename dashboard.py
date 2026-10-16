"""Servidor HTTP + SSE del dashboard (solo libreria estandar)."""
import json
import os
import queue
import signal
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import events
import replay
from config import log

HERE = os.path.dirname(os.path.abspath(__file__))


class App:
    """Estado compartido del servidor: escenarios, narrador, directorios y lock de un-escenario-a-la-vez."""

    def __init__(self, scenario_fn, scenarios, narrator=None, web_dir=None, recordings_dir=None) -> None:
        self.scenario_fn = scenario_fn
        self.scenarios = list(scenarios)
        self.narrator = narrator
        self.web_dir = web_dir or os.path.join(HERE, "web")
        self.recordings_dir = recordings_dir or os.path.join(HERE, "recordings")
        self.busy = threading.Lock()
        self.voice_on = narrator is not None


def _live_worker(app: App, name: str, q: queue.Queue) -> None:
    rec = replay.Recorder(app.recordings_dir)
    rec.start()
    emit = rec.wrap(q.put)
    chain = app.narrator.wrap(emit) if app.narrator else emit
    events.set_emitter(chain)
    ok = True
    try:
        app.scenario_fn(name, chain)
    except Exception as e:  # noqa: BLE001
        ok = False
        log("dashboard", f"escenario {name} fallo: {type(e).__name__}: {e}")
        chain({"type": "error", "text": f"{type(e).__name__}: {e}"})
        chain({"type": "done", "scenario": name})
    if ok and name != "reset" and not any(i["ev"].get("type") == "error" for i in rec.items):
        rec.save(name)


def make_server(app: App, port: int = 8787) -> ThreadingHTTPServer:
    """Crea el servidor en 127.0.0.1 (port 0 = libre)."""

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silencio
            pass

        def _send(self, code: int, body: bytes, ctype: str = "text/plain; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _file(self, path: str, ctype: str) -> None:
            if not os.path.isfile(path):
                return self._send(404, b"not found")
            with open(path, "rb") as f:
                self._send(200, f.read(), ctype)

        def do_GET(self) -> None:  # noqa: N802
            p = self.path.split("?")[0]
            if p in ("/", "/index.html"):
                return self._file(os.path.join(app.web_dir, "index.html"), "text/html; charset=utf-8")
            if p == "/healthz":
                return self._send(200, b"ok")
            if p == "/api/state":
                off = [s for s in app.scenarios if replay.find_recording(app.recordings_dir, s)]
                return self._send(200, json.dumps({"scenarios": app.scenarios, "offline": off,
                                                   "voice": app.voice_on}).encode(), "application/json")
            if p.startswith("/audio/"):
                return self._file(os.path.join(app.web_dir, "audio", os.path.basename(p)), "audio/mpeg")
            for prefix, live in (("/scenario/", True), ("/playback/", False)):
                if p.startswith(prefix):
                    name = p[len(prefix):]
                    if name not in app.scenarios:
                        return self._send(404, b"unknown scenario")
                    return self._sse(name, live)
            self._send(404, b"not found")

        def _sse(self, name: str, live: bool) -> None:
            if not app.busy.acquire(blocking=False):
                return self._send(409, b"busy")
            try:
                q: queue.Queue = queue.Queue()
                if live:
                    threading.Thread(target=_live_worker, args=(app, name, q), daemon=True).start()
                else:
                    threading.Thread(target=self._playback, args=(name, q), daemon=True).start()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                while True:
                    try:
                        ev = q.get(timeout=15)
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                        continue
                    self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
                    self.wfile.flush()
                    if ev.get("type") == "done":
                        break
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                events.set_emitter(None)
                app.busy.release()

        def _playback(self, name: str, q: queue.Queue) -> None:
            p = replay.find_recording(app.recordings_dir, name)
            if not p:
                q.put({"type": "error", "text": f"no recording for {name}"})
                q.put({"type": "done", "scenario": name})
                return
            replay.replay(replay.load(p), q.put)

    return ThreadingHTTPServer(("127.0.0.1", port), H)


def main() -> None:
    """CLI: --port, --freeze, --no-voice, --prerender."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.getenv("DASHBOARD_PORT", "8787")))
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--no-voice", action="store_true")
    ap.add_argument("--prerender", action="store_true")
    a = ap.parse_args()
    rec_dir = os.path.join(HERE, "recordings")
    if a.freeze:
        log("dashboard", f"congeladas: {replay.freeze(rec_dir)}")
        return
    import voice
    if a.prerender:
        n = voice.prerender()
        print(f"{n}/10 lineas de narracion listas en {voice.AUDIO_DIR}")
        return
    from narrator import Narrator
    from scenarios import SCENARIOS, Session
    if not os.getenv("OPENAI_API_KEY"):
        log("dashboard", "falta OPENAI_API_KEY (el modo offline igual anda)")
    sess = Session()
    app = App(sess.run, SCENARIOS, None if a.no_voice else Narrator(voice.narrate))
    srv = make_server(app, a.port)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    log("dashboard", f"http://localhost:{a.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if sess.mem:
                sess.mem.close()
        finally:
            import box
            box.teardown()


if __name__ == "__main__":
    main()
