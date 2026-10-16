"""Memoria de defensa en SurrealDB: el guardrail APRENDE de los ataques que se cuelan.

La denylist de rutas NO esta hardcodeada: se lee de la base. Cuando un ataque se cuela (LEAKED),
se registra el incidente y se aprende su ruta; desde ahi queda bloqueada.
Engine por defecto: embebido `surrealkv://` (persiste a disco, sin Docker ni auth).
  SURREAL_URL vacio      -> surrealkv://<SURREAL_PATH o ./.surreal_data>
  SURREAL_URL=mem://     -> en memoria del proceso (tests)
  SURREAL_URL=ws://...   -> server externo (con signin)
Si la base falla, degrada a un set en proceso (la demo sigue).
"""
from __future__ import annotations

import os

from config import SEED_INDICATORS


def _default_url() -> str:
    url = os.getenv("SURREAL_URL", "").strip()
    if not url:
        return "surrealkv://" + os.path.abspath(os.getenv("SURREAL_PATH", "./.surreal_data"))
    return url


class DefenseMemory:
    def __init__(self) -> None:
        self.db = None
        self.engine = "fallback"
        self._fallback: set[str] = set()
        url = _default_url()
        try:
            from surrealdb import Surreal

            db = Surreal(url)
            if url.startswith(("ws://", "wss://", "http://", "https://")):
                db.signin({"username": os.getenv("SURREAL_USER", "root"),
                           "password": os.getenv("SURREAL_PASS", "root")})
            db.use(os.getenv("SURREAL_NS", "redteam"), os.getenv("SURREAL_DB", "memory"))
            db.query("DEFINE TABLE IF NOT EXISTS incident SCHEMALESS;")
            db.query("DEFINE TABLE IF NOT EXISTS learned_path SCHEMALESS;")
            self.db = db
            self.engine = url.split(":")[0]  # surrealkv | mem | ws ...
        except Exception as e:  # noqa: BLE001
            self.engine = f"fallback ({type(e).__name__})"

    # --- lectura: la politica que conoce el guardrail (seed + aprendido) ---
    def sensitive_paths(self) -> set[str]:
        out = set(SEED_INDICATORS)
        if self.db is not None:
            try:
                rows = self.db.query("SELECT * FROM learned_path;")  # `value` es palabra reservada -> SELECT *
                out |= {r["value"] for r in (rows or []) if isinstance(r, dict) and r.get("value")}
            except Exception:  # noqa: BLE001
                pass
        return out | self._fallback

    def learned_rows(self) -> list[dict]:
        """Lo aprendido (sin seed): [{value, from_attack}]. Para mostrar en el dashboard."""
        if self.db is not None:
            try:
                return [r for r in (self.db.query("SELECT * FROM learned_path;") or []) if isinstance(r, dict)]
            except Exception:  # noqa: BLE001
                pass
        return [{"value": v, "from_attack": "?"} for v in sorted(self._fallback)]

    # --- escritura: registrar un incidente y, si se colo, aprender su ruta ---
    def record_incident(self, *, attack: str, technique: str, target_path: str,
                        dest_domain: str, verdict: str) -> None:
        if self.db is not None:
            try:
                self.db.create("incident", {"attack": attack, "technique": technique,
                                            "target_path": target_path, "dest_domain": dest_domain,
                                            "verdict": verdict})
                if verdict == "LEAKED" and target_path:
                    self.db.query("DELETE learned_path WHERE value = $v;", {"v": target_path})  # idempotente
                    self.db.create("learned_path", {"value": target_path, "from_attack": attack})
                return
            except Exception:  # noqa: BLE001
                pass
        if verdict == "LEAKED" and target_path:
            self._fallback.add(target_path)

    def incident_count(self) -> int:
        if self.db is not None:
            try:
                r = self.db.query("SELECT count() FROM incident GROUP ALL;")
                return int(r[0]["count"]) if r else 0
            except Exception:  # noqa: BLE001
                pass
        return 0

    def reset(self) -> None:
        """Olvida todo lo aprendido (para mostrar el arco vacio -> aprende)."""
        self._fallback.clear()
        if self.db is not None:
            try:
                self.db.query("DELETE learned_path; DELETE incident;")
            except Exception:  # noqa: BLE001
                pass

    def close(self) -> None:
        if self.db is not None:
            try:
                self.db.close()
            except Exception:  # noqa: BLE001
                pass
