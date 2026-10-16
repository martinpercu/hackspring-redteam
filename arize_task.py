"""Tarea online `injection_judge` (LLM-as-judge continuo) sobre los spans LLM del proyecto."""
import os
import sys
from datetime import datetime, timedelta, timezone

from config import log

PROJECT = os.getenv("ARIZE_PROJECT_NAME", "redteam-live")
EVALUATOR = "injection_judge"
TASK = f"injection_judge_{PROJECT}"  # una tarea por proyecto


def _client():
    from arize import ArizeClient

    return ArizeClient(api_key=os.environ["ARIZE_API_KEY"])


def _find_task(c, space: str):
    return next((t for t in c.tasks.list(space=space).tasks if t.name == TASK), None)


def list_state(c, space: str) -> None:
    """Imprime si existen el evaluador y la tarea."""
    evs = [e.name for e in c.evaluators.list(space=space).evaluators]
    print(f"evaluador {EVALUATOR}: {'EXISTE' if EVALUATOR in evs else 'NO existe'}")
    print(f"tarea {TASK}: {'EXISTE' if _find_task(c, space) else 'NO existe'}")


def create_task(c, space: str) -> None:
    """Crea la tarea continua si no existe."""
    if _find_task(c, space):
        log("arize", f"tarea {TASK} ya existe")
        return
    from arize._generated.api_client.models.span_evaluator_input import SpanEvaluatorInput
    from arize.tasks.types import TaskEvaluatorInput

    ev = next((e for e in c.evaluators.list(space=space).evaluators if e.name == EVALUATOR), None)
    if ev is None:
        raise RuntimeError(f"falta el evaluador {EVALUATOR} en el space (crearlo en la UI)")
    project = next((p for p in c.projects.list(name=PROJECT, space=space).projects if p.name == PROJECT), None)
    if project is None:
        raise RuntimeError(f"no existe el proyecto {PROJECT} (mandar trazas primero)")
    c.tasks.create_evaluation_task(
        name=TASK, task_type="TEMPLATE_EVALUATION",
        evaluators=[TaskEvaluatorInput(SpanEvaluatorInput(
            evaluator_id=ev.id, query_filter="span_kind = 'LLM'",
            column_mappings={"input": "attributes.input.value", "output": "attributes.output.value"}))],
        project=project.id, space=space, sampling_rate=1.0, is_continuous=True)
    log("arize", f"tarea {TASK} creada")


def backfill(c, space: str, hours: float) -> None:
    """Evalua los spans LLM de las ultimas H horas."""
    end = datetime.now(timezone.utc)
    run = c.tasks.trigger_run(task=TASK, space=space, data_start_time=end - timedelta(hours=hours),
                              data_end_time=end, max_spans=500, override_evaluations=True)
    done = c.tasks.wait_for_run(run_id=run.id, timeout=900)
    log("arize", f"backfill {getattr(done, 'status', done)}")


def main(argv: list[str]) -> int:
    space = os.environ["ARIZE_SPACE_ID"]
    c = _client()
    if "--list" in argv:
        list_state(c, space)
    elif "--backfill" in argv:
        backfill(c, space, float(argv[argv.index("--backfill") + 1]))
    else:
        create_task(c, space)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
