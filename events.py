"""Emisor de eventos para el dashboard. Por defecto no-op (modo CLI). Cero dependencias."""
_EMIT = None


def set_emitter(fn) -> None:
    global _EMIT
    _EMIT = fn


def emit(**ev) -> None:
    if _EMIT is not None:
        try:
            _EMIT(ev)
        except Exception:  # noqa: BLE001
            pass
