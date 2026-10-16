import events
import tracing


def test_emit_without_emitter_is_noop():
    events.set_emitter(None)
    events.emit(type="x")


def test_emitter_exceptions_are_swallowed():
    def bad(ev):
        raise RuntimeError("boom")
    events.set_emitter(bad)
    try:
        events.emit(type="x")          # no debe propagar
    finally:
        events.set_emitter(None)


def test_tracing_off_gives_null_span():
    assert tracing.tracing_enabled() is False
    with tracing.span("x", "CHAIN", a=1) as sp:
        sp.set_attribute("k", "v")
        tracing.set_status(sp, True)
        assert tracing.span_id_hex(sp) is None
