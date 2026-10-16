"""Sandbox Daytona unico y reusable. SDK importado perezosamente."""
import os
import sys

from config import log

_DAYTONA = None
_SANDBOX = None


def client():
    """Cliente Daytona (se crea una vez)."""
    global _DAYTONA
    if _DAYTONA is None:
        from daytona import Daytona, DaytonaConfig

        _DAYTONA = Daytona(DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"]))
    return _DAYTONA


def sandbox():
    """Crea el sandbox la primera vez y lo reusa despues."""
    global _SANDBOX
    if _SANDBOX is None:
        log("daytona", "creando sandbox...")
        if os.getenv("SANDBOX_HARDEN") == "1":
            from daytona import CreateSandboxFromSnapshotParams

            _SANDBOX = client().create(CreateSandboxFromSnapshotParams(
                ephemeral=True, auto_stop_interval=30, labels={"app": "agent-red-team"}))
        else:
            _SANDBOX = client().create()
    return _SANDBOX


def teardown() -> None:
    """Borra el sandbox (idempotente)."""
    global _SANDBOX
    if _SANDBOX is None:
        return
    try:
        client().delete(_SANDBOX)
        log("daytona", "sandbox borrado")
    except Exception as e:  # noqa: BLE001
        log("daytona", f"no pude borrar el sandbox ({type(e).__name__}): borralo a mano en el dashboard de Daytona")
    _SANDBOX = None


def exec_shell(cmd: str, timeout: int = 30) -> str:
    """Corre cmd en el sandbox; devuelve stdout+stderr (max 4000 chars)."""
    r = sandbox().process.exec(cmd, timeout=timeout)
    return ((r.result or "") + (getattr(r, "stderr", "") or ""))[:4000]


def selftest() -> bool:
    """Exec + upload en un sandbox real; siempre lo borra."""
    try:
        out = exec_shell("echo hola-desde-el-sandbox && python3 --version")
        print("exec:", out.strip().replace("\n", " / "))
        sandbox().fs.upload_file(b"selftest", "/home/daytona/selftest.txt")
        back = exec_shell("cat /home/daytona/selftest.txt")
        ok = "hola-desde-el-sandbox" in out and back.strip() == "selftest"
        print("fs.upload_file:", "ok" if back.strip() == "selftest" else "FAIL")
        return ok
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}"[:300])
        return False
    finally:
        teardown()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        ok = selftest()
        print("SELFTEST OK" if ok else "SELFTEST FAIL")
        sys.exit(0 if ok else 1)
