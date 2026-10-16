"""Sube la evaluacion nativa `hijacked` a Arize para cada span de ataque."""
import os

from config import log
from tracing import tracing_enabled


def log_evals(results: list[dict]) -> int:
    """Sube eval.hijacked.* por resultado con span_id; devuelve cuantas filas subio."""
    space_id, api_key = os.getenv("ARIZE_SPACE_ID"), os.getenv("ARIZE_API_KEY")
    rows = [r for r in results if r.get("span_id")]
    if not (space_id and api_key) or not tracing_enabled() or not rows:
        log("arize", "evals: nada que subir (sin keys, TRACING=off o sin span_id)")
        return 0
    try:
        import pandas as pd
        from arize import ArizeClient

        df = pd.DataFrame([{
            "context.span_id": r["span_id"],
            "eval.hijacked.label": "hijacked" if r.get("leaked") else "resisted",
            "eval.hijacked.score": 1.0 if r.get("leaked") else 0.0,
            "eval.hijacked.explanation": f"[{r.get('mode')}] {r.get('verdict')}: {r.get('detail')}",
        } for r in rows])
        ArizeClient(api_key=api_key).spans.update_evaluations(
            space_id=space_id, project_name=os.getenv("ARIZE_PROJECT_NAME", "redteam-live"), dataframe=df)
        log("arize", f"evals: {len(df)} evaluaciones `hijacked` subidas")
        return len(df)
    except Exception as e:  # noqa: BLE001
        log("arize", f"evals fallo ({type(e).__name__}: {str(e)[:150]})")
        return 0
