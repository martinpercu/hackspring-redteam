"""Convierte eventos del motor en lineas habladas de dos voces."""
from config import log

LINES = {
    "intro_known": ("attacker", "A harmless page. One hidden instruction. Let's see if the agent obeys."),
    "intro_guarded": ("defender", "Same attack. This time the tools have gates."),
    "intro_unseen": ("attacker", "A new trick: a path nobody has seen, and a trusted domain to hide behind."),
    "intro_replay": ("defender", "Same new attack. Let's see if it remembers."),
    "leaked": ("attacker", "It obeyed. The decoy credential just left the sandbox."),
    "leaked_unseen": ("attacker", "It got through. Once."),
    "blocked": ("defender", "Blocked. The shell refused the sensitive path, and the egress gate refused the domain."),
    "blocked_learned": ("defender", "Blocked. It remembered."),
    "safe": ("defender", "The agent ignored the injection."),
    "learned": ("defender", "Learned. That path now lives in SurrealDB, and the guardrail reads it from there."),
}


def line_key(ev: dict) -> str | None:
    """Clave de LINES para un evento, o None."""
    t = ev.get("type")
    guarded = ev.get("mode") == "guarded"
    if t == "attack_start":
        if not guarded:
            return "intro_known"
        return "intro_unseen" if ev.get("unseen") else "intro_guarded"
    if t == "verdict":
        v = ev.get("verdict")
        if v == "LEAKED":
            return "leaked_unseen" if guarded else "leaked"
        if v == "BLOCKED":
            return "blocked_learned" if ev.get("unseen") else "blocked"
        if v == "SAFE":
            return "safe"
    if t == "memory_learn":
        return "learned"
    return None


class Narrator:
    """Agrega eventos `say` (con audio opcional) detras de los eventos relevantes."""

    def __init__(self, narrate_fn, enabled: bool = True) -> None:
        self.narrate_fn = narrate_fn
        self.enabled = enabled
        self.scenario = ""
        self.quiet = False

    def _say(self, emit, who: str, text: str) -> None:
        try:
            audio = self.narrate_fn(text, who)
        except Exception as e:  # noqa: BLE001
            log("narrator", f"voz fallo: {type(e).__name__}")
            audio = None
        emit({"type": "say", "who": who, "text": text, "audio": audio})

    def wrap(self, emit):
        """Devuelve un emisor que reenvia y agrega `say`."""
        def f(ev: dict) -> None:
            emit(ev)
            if ev.get("type") == "scenario_start":
                self.scenario = ev.get("scenario", "")
                self.quiet = self.scenario == "battery"
                return
            if not self.enabled:
                return
            if ev.get("type") == "summary":
                self._say(emit, "defender", ev.get("text", ""))
                return
            if self.quiet:
                return
            key = line_key(ev)
            if key == "intro_unseen" and self.scenario == "replay":
                key = "intro_replay"
            if key:
                who, text = LINES[key]
                self._say(emit, who, text)
        return f
