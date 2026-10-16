"""Corre TODOS los tests sin pytest:  python tests/run_all.py [filtro]
Los tests son offline y deterministas: no usan LLM, ni Daytona, ni red, ni Arize."""
import glob
import importlib.util
import os
import sys
import traceback

os.environ["TRACING"] = "off"          # los tests NO deben ensuciar el proyecto de Arize
os.environ["SURREAL_URL"] = "mem://"   # memoria en proceso, sin tocar disco
os.environ.pop("VICTIM_MODEL", None)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))   # para `import helpers`

flt = sys.argv[1] if len(sys.argv) > 1 else ""
ok = fail = 0
for path in sorted(glob.glob(os.path.join(ROOT, "tests", "test_*.py"))):
    if flt and flt not in os.path.basename(path):
        continue
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:  # noqa: BLE001
        fail += 1
        print(f"FAIL  {os.path.basename(path)}  (import)\n{traceback.format_exc()}")
        continue
    for name in sorted(n for n in dir(mod) if n.startswith("test_")):
        try:
            getattr(mod, name)()
            ok += 1
            print(f"ok    {os.path.basename(path)}::{name}")
        except Exception:  # noqa: BLE001
            fail += 1
            print(f"FAIL  {os.path.basename(path)}::{name}\n{traceback.format_exc()}")
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
