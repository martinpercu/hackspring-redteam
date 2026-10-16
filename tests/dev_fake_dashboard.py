"""Dashboard con motor SIMULADO (sin red, sin LLM, sin keys): para desarrollar/probar la UI. Puerto 8791.
   Uso:  python tests/dev_fake_dashboard.py   ->  http://127.0.0.1:8791"""
import os, sys, tempfile
os.environ["TRACING"] = "off"; os.environ["SURREAL_URL"] = "mem://"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "tests")]
import dashboard as D
from helpers import URLS, CANARIES, fake_exec, fake_fetch, mixed_victim
from narrator import Narrator
from scenarios import SCENARIOS, Session
sess = Session(setup_fn=lambda: (URLS, CANARIES), victim_fn=mixed_victim, exec_fn=fake_exec, fetch_fn=fake_fetch)
app = D.App(sess.run, SCENARIOS, Narrator(lambda t, w: None), recordings_dir=tempfile.mkdtemp())
srv = D.make_server(app, 8791)
print("listo en 8791", flush=True)
srv.serve_forever()
