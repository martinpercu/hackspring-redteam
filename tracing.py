"""Trazas Arize AX (OpenTelemetry). Si no hay keys o TRACING=off -> todo es no-op y el resto sigue andando."""
from __future__ import annotations

import contextlib
import os

import config
from config import log

_TRACER = None
_INIT = False


def tracing_enabled() -> bool:
    return os.getenv("TRACING", "on").lower() != "off"


def setup_tracing():
    """Devuelve un tracer (AX si hay keys) o None. Idempotente."""
    global _TRACER, _INIT
    if _INIT:
        return _TRACER
    _INIT = True
    space_id, api_key = os.getenv("ARIZE_SPACE_ID"), os.getenv("ARIZE_API_KEY")
    if not tracing_enabled() or not (space_id and api_key):
        log("arize", "tracing OFF (TRACING=off o sin keys)")
        return None
    try:
        from arize.otel import register

        tp = register(space_id=space_id, api_key=api_key,
                      project_name=os.getenv("ARIZE_PROJECT_NAME", "redteam-live"),
                      batch=False)  # scripts cortos: export inmediato
        try:
            from openinference.instrumentation.openai import OpenAIInstrumentor

            OpenAIInstrumentor().instrument(tracer_provider=tp)  # spans LLM con mensajes + tool_calls
            log("arize", "OpenAI instrumentado (spans LLM)")
        except Exception as e:  # noqa: BLE001
            log("arize", f"OpenAI sin instrumentar ({e})")
        _TRACER = tp.get_tracer("redteam")
        log("arize", "AX tracing ON")
    except Exception as e:  # noqa: BLE001
        log("arize", f"AX fallo ({e}) — sigo sin trazas")
    return _TRACER


class _NullSpan:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def set_attribute(self, *a, **k):
        pass

    def get_span_context(self):
        return None


@contextlib.contextmanager
def span(name: str, kind: str = "TOOL", **attrs):
    """Context manager de span (kind: TOOL | CHAIN | LLM | RETRIEVER | EVALUATOR). No-op sin tracing."""
    t = setup_tracing()
    if t is None:
        yield _NullSpan()
        return
    with t.start_as_current_span(name) as s:
        for k, v in attrs.items():
            try:
                s.set_attribute(k, v)
            except Exception:  # noqa: BLE001
                pass
        try:
            from openinference.semconv.trace import SpanAttributes

            s.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, kind)
        except Exception:  # noqa: BLE001
            pass
        yield s


def set_status(sp, ok: bool, msg: str = "") -> None:
    """Verde si ok, rojo si no (visible en la UI de Arize)."""
    try:
        from opentelemetry.trace import Status, StatusCode

        sp.set_status(Status(StatusCode.OK) if ok else Status(StatusCode.ERROR, msg))
    except Exception:  # noqa: BLE001
        pass


def span_id_hex(sp) -> str | None:
    try:
        return format(sp.get_span_context().span_id, "016x")
    except Exception:  # noqa: BLE001
        return None


def flush() -> None:
    """Fuerza el envio de spans pendientes (llamar antes de salir de un script corto)."""
    try:
        from opentelemetry import trace

        tp = trace.get_tracer_provider()
        if hasattr(tp, "force_flush"):
            tp.force_flush()
    except Exception:  # noqa: BLE001
        pass
