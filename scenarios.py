"""Escenarios del dashboard: cada boton es un escenario sobre un rango compartido."""
from __future__ import annotations

import threading
import time

import fixtures
import runner
from config import log

SCENARIOS = ["reset", "attack_nodef", "attack_def", "unseen", "replay", "control", "battery"]


def default_setup():
    """Crea el rango real en Daytona: (urls, [canary, canary2])."""
    import range_setup
    c1, c2 = range_setup.new_canary(), range_setup.new_canary()
    return range_setup.setup_range(c1, c2), [c1, c2]


class Session:
    """Rango + memoria compartidos entre escenarios (se crean una sola vez)."""

    def __init__(self, setup_fn=None, **engine_kw) -> None:
        self.setup_fn = setup_fn or default_setup
        self.kw = engine_kw
        self.lock = threading.Lock()
        self.ready = False
        self.urls: dict = {}
        self.canaries: list = []
        self.mem = None
        self.sid = ""

    def ensure(self) -> None:
        """Inicializa tracing, rango y memoria una sola vez."""
        if self.ready:
            return
        with self.lock:
            if self.ready:
                return
            from memory import DefenseMemory
            from tracing import setup_tracing
            setup_tracing()
            self.urls, self.canaries = self.setup_fn()
            self.mem = DefenseMemory()
            self.sid = f"dash-{int(time.time())}"
            self.ready = True

    def _attack(self, atk, guarded):
        return runner.run_attack(atk, self.urls[atk["name"]], self.canaries, guarded, self.sid,
                                 mem=self.mem, **self.kw)

    def _battery(self, emit) -> None:
        b = runner.battery(self.urls, self.canaries, self.sid, self.mem, **self.kw)
        try:
            import arize_evals
            n = arize_evals.log_evals(b["base"] + b["guard"])
            if n:
                emit({"type": "info", "text": f"{n} evals uploaded to Arize"})
        except Exception as e:  # noqa: BLE001
            log("arize", f"evals fallo: {type(e).__name__}")
        emit({"type": "summary", "text": runner.summary_sentence(b)})

    def _state(self, emit) -> None:
        emit({"type": "memory_state", "paths": sorted(self.mem.sensitive_paths())})

    def run(self, name: str, emit) -> None:
        """Ejecuta un escenario emitiendo eventos."""
        if name not in SCENARIOS:
            emit({"type": "error", "text": f"unknown scenario: {name}"})
            emit({"type": "done", "scenario": name})
            return
        self.ensure()
        emit({"type": "scenario_start", "scenario": name})
        self._state(emit)
        if name == "reset":
            self.mem.reset()
            emit({"type": "info", "text": "Defense memory reset"})
        elif name == "attack_nodef":
            self._attack(fixtures.known_attacks()[0], False)
        elif name == "attack_def":
            self._attack(fixtures.known_attacks()[0], True)
        elif name in ("unseen", "replay"):
            self._attack(fixtures.unseen_attack(), True)
        elif name == "control":
            ctl = fixtures.CONTROLS[0]
            runner.run_control(ctl, self.urls[ctl["name"]], self.canaries, True, self.sid,
                               mem=self.mem, **self.kw)
        elif name == "battery":
            self._battery(emit)
        self._state(emit)
        emit({"type": "done", "scenario": name})
