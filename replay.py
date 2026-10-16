"""Grabar y reproducir corridas del dashboard (modo offline, sin red)."""
import json
import os
import shutil
import time


class Recorder:
    """Acumula eventos con marca de tiempo y los guarda como JSON."""

    def __init__(self, directory: str = "recordings") -> None:
        self.dir = directory
        self.items: list[dict] = []
        self.t0 = time.time()

    def start(self) -> None:
        """Vacia la grabacion y fija t0."""
        self.items = []
        self.t0 = time.time()

    def add(self, ev: dict) -> None:
        """Agrega un evento con su tiempo relativo."""
        self.items.append({"t": round(time.time() - self.t0, 3), "ev": ev})

    def wrap(self, emit):
        """Devuelve un emisor que graba y reenvia."""
        def f(ev: dict) -> None:
            self.add(ev)
            emit(ev)
        return f

    def save(self, scenario: str, sub: str = "last") -> str:
        """Escribe <dir>/<sub>/<scenario>.json y devuelve la ruta."""
        d = os.path.join(self.dir, sub)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, scenario + ".json")
        with open(path, "w") as f:
            json.dump(self.items, f)
        return path


def load(path: str) -> list[dict]:
    """Lee una grabacion."""
    with open(path) as f:
        return json.load(f)


def find_recording(directory: str, scenario: str) -> str | None:
    """Ruta de la grabacion (demo/ gana sobre last/) o None."""
    for sub in ("demo", "last"):
        p = os.path.join(directory, sub, scenario + ".json")
        if os.path.exists(p):
            return p
    return None


def replay(items: list[dict], emit, speed: float = 1.0, max_gap: float = 1.2) -> None:
    """Reproduce los eventos acotando las esperas largas."""
    prev = None
    for it in items:
        if prev is not None:
            time.sleep(min(max(it["t"] - prev, 0), max_gap) / speed)
        prev = it["t"]
        emit(it["ev"])


def freeze(directory: str) -> list[str]:
    """Copia last/*.json a demo/ y devuelve los nombres."""
    src, dst = os.path.join(directory, "last"), os.path.join(directory, "demo")
    names = sorted(n for n in os.listdir(src) if n.endswith(".json")) if os.path.isdir(src) else []
    os.makedirs(dst, exist_ok=True)
    for n in names:
        shutil.copy(os.path.join(src, n), os.path.join(dst, n))
    return names
