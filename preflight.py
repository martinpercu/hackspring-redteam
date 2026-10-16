"""Preflight: 1 llamada minima por sponsor -> tabla PASS / FAIL / SKIP. No importa nada del proyecto."""
import os
import socket
import sys
import time

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # noqa: BLE001
    pass


class Skip(Exception):
    """El check no corre (falta una key o no se probo)."""


def need(*names: str) -> None:
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        raise Skip("falta " + ", ".join(missing))


def check_net() -> str:
    for host in ("api.openai.com", "app.daytona.io", "api.elevenlabs.io"):
        socket.create_connection((host, 443), timeout=8).close()
    return "DNS+TCP 443 ok a openai/daytona/elevenlabs"


def check_daytona() -> str:
    need("DAYTONA_API_KEY")
    from daytona import Daytona, DaytonaConfig

    d = Daytona(DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"]))
    t0 = time.time()
    sb = d.create()
    try:
        took = time.time() - t0
        r = sb.process.exec("echo hola && python3 --version", timeout=30)
        if r.exit_code != 0:
            raise RuntimeError(f"exec exit_code={r.exit_code}")
        url = str(sb.create_signed_preview_url(8080, expires_in_seconds=60).url)
        if not url.startswith("http"):
            raise RuntimeError("preview URL invalida")
        return f"sandbox en {took:.1f}s · exec ok · preview URL ok"
    finally:
        try:
            d.delete(sb)
        except Exception as e:  # noqa: BLE001
            print(f"  !! no pude borrar el sandbox ({type(e).__name__}); borralo a mano en app.daytona.io")


def check_openai() -> str:
    need("OPENAI_API_KEY")
    from openai import OpenAI

    model = os.getenv("VICTIM_MODEL", "gpt-4o-mini")
    resp = OpenAI().chat.completions.create(
        model=model, temperature=0, max_tokens=5,
        messages=[{"role": "user", "content": "Reply with the single word: ok"}])
    return f"modelo {model} responde: {(resp.choices[0].message.content or '').strip()[:20]!r}"


def check_arize() -> str:
    need("ARIZE_SPACE_ID", "ARIZE_API_KEY")
    from arize.otel import register

    space_id, api_key = os.environ["ARIZE_SPACE_ID"], os.environ["ARIZE_API_KEY"]
    tp = register(space_id=space_id, api_key=api_key,
                  project_name=os.getenv("ARIZE_PROJECT_NAME", "redteam-live"), batch=False)
    with tp.get_tracer("preflight").start_as_current_span("preflight.ping") as s:
        s.set_attribute("input.value", "preflight")
        sid = format(s.get_span_context().span_id, "016x")
    info = "evaluador injection_judge: ?"
    try:
        from arize import ArizeClient

        res = ArizeClient(api_key=api_key).evaluators.list(space=space_id)
        names = [getattr(e, "name", "") for e in (getattr(res, "evaluators", None) or [])]
        info = "evaluador injection_judge: " + ("EXISTE" if "injection_judge" in names else "no existe")
    except Exception as e:  # noqa: BLE001
        info = f"evaluators.list fallo ({type(e).__name__})"
    return f"span enviado ({sid}) · {info}"


def check_eleven() -> str:
    need("ELEVENLABS_API_KEY")
    from elevenlabs.client import ElevenLabs

    audio = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"]).text_to_speech.convert(
        text="Preflight ok.", voice_id=os.getenv("ELEVENLABS_VOICE_ID") or "JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2", output_format="mp3_44100_128")
    n = sum(len(c) for c in audio if c)
    if n <= 1000:
        raise RuntimeError(f"mp3 demasiado chico ({n} bytes)")
    return f"mp3 de {n} bytes"


def check_surreal() -> str:
    from surrealdb import Surreal

    db = Surreal("mem://")
    db.use("redteam", "memory")
    db.create("preflight", {"ok": True})
    rows = db.query("SELECT * FROM preflight;")
    db.close()
    if not rows:
        raise RuntimeError("select vacio")
    return "embebido mem:// ok (create + select)"


def check_anchor() -> str:
    need("ANCHORBROWSER_API_KEY")
    from anchorbrowser import Anchorbrowser

    b = Anchorbrowser(api_key=os.environ["ANCHORBROWSER_API_KEY"]).billing.get_billing()
    return f"billing ok: {str(b)[:120]}"


def check_harden() -> str:
    need("DAYTONA_API_KEY")
    from daytona import CreateSandboxFromSnapshotParams, Daytona, DaytonaConfig

    d = Daytona(DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"]))
    sb = d.create(CreateSandboxFromSnapshotParams(
        ephemeral=True, auto_stop_interval=30, labels={"app": "agent-red-team"}))
    try:
        r = sb.process.exec("echo ok", timeout=30)
        if r.exit_code != 0:
            raise RuntimeError(f"exec exit_code={r.exit_code}")
        return "SANDBOX_HARDEN=1 es seguro de usar"
    finally:
        try:
            d.delete(sb)
        except Exception as e:  # noqa: BLE001
            print(f"  !! no pude borrar el sandbox ({type(e).__name__}); borralo a mano en app.daytona.io")


# nombre -> (funcion, critico)
CHECKS = {
    "net": (check_net, False),
    "daytona": (check_daytona, True),
    "openai": (check_openai, True),
    "arize": (check_arize, False),
    "eleven": (check_eleven, False),
    "surreal": (check_surreal, False),
    "anchor": (check_anchor, False),
    "harden": (check_harden, False),
}


def run(name: str) -> tuple[str, str]:
    """Corre un check y devuelve (PASS|FAIL|SKIP, detalle)."""
    try:
        return "PASS", CHECKS[name][0]()
    except Skip as e:
        return "SKIP", str(e)
    except Exception as e:  # noqa: BLE001
        return "FAIL", f"{type(e).__name__}: {e}"[:200]


def main(argv: list[str]) -> int:
    only = argv[argv.index("--only") + 1] if "--only" in argv and argv.index("--only") + 1 < len(argv) else None
    if only and only not in CHECKS:
        print(f"check desconocido: {only} (opciones: {', '.join(CHECKS)})")
        return 2
    names = [only] if only else [n for n in CHECKS if n != "harden"]
    print(f"{'CHECK':9} {'RESULT':6} DETAIL")
    bad_critical = False
    for n in names:
        status, detail = run(n)
        print(f"{n:9} {status:6} {detail}", flush=True)
        if CHECKS[n][1] and status != "PASS":
            bad_critical = True
    print("PREFLIGHT FALLO" if bad_critical else "PREFLIGHT OK")
    return 1 if bad_critical else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
