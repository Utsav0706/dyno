"""Copy runs from another Dyno database into this one (`dyno import`).

Each CI eval run writes its own dyno.db (an artifact GitHub deletes after 30 days);
labelling, calibration and comparing a baseline with a later run need them in one
place. Run ids are random, so they're kept as they are; result and step ids are
numbered by each database, so they're renumbered here. Runs already present are
skipped, which makes importing the same file twice harmless.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from dyno.store.db import Store, open_engine
from dyno.store.models import Label, Result, Run, RunCase, ScoreRow, StepRow

_RUN_COLS = [c.key for c in Run.__mapper__.column_attrs]
_CASE_COLS = [c.key for c in RunCase.__mapper__.column_attrs if c.key != "run_id"]
_RESULT_COLS = [c.key for c in Result.__mapper__.column_attrs if c.key not in ("id", "run_id")]
_STEP_COLS = [c.key for c in StepRow.__mapper__.column_attrs if c.key not in ("id", "result_id")]
_SCORE_COLS = [c.key for c in ScoreRow.__mapper__.column_attrs if c.key not in ("id", "result_id")]
_LABEL_COLS = [c.key for c in Label.__mapper__.column_attrs if c.key not in ("id", "result_id")]


def _copy(obj: object, cols: list[str]) -> dict:
    return {c: getattr(obj, c) for c in cols}


def import_runs(source_url: str, store: Store) -> tuple[list[str], list[str]]:
    """Copy every run in `source_url` that `store` lacks. Returns (imported, skipped)."""
    source = open_engine(source_url)  # also brings an older Dyno file up to date
    with Session(store.engine) as dest:
        have = set(dest.scalars(select(Run.id)))
    imported: list[str] = []
    skipped: list[str] = []
    with Session(source) as src, Session(store.engine) as dest, dest.begin():
        runs = src.scalars(
            select(Run).options(
                selectinload(Run.cases),
                selectinload(Run.results).selectinload(Result.steps),
                selectinload(Run.results).selectinload(Result.scores),
            )
        ).all()
        labels = src.scalars(select(Label)).all()
        labels_by_result: dict[int, list[Label]] = {}
        for lab in labels:
            labels_by_result.setdefault(lab.result_id, []).append(lab)

        for run in runs:
            if run.id in have:
                skipped.append(run.id)
                continue
            new = Run(**_copy(run, _RUN_COLS))
            new.cases = [RunCase(**_copy(c, _CASE_COLS)) for c in run.cases]
            dest.add(new)
            dest.flush()  # the run and its cases first: results point at them
            for r in run.results:
                row = Result(run_id=run.id, **_copy(r, _RESULT_COLS))
                row.steps = [StepRow(**_copy(s, _STEP_COLS)) for s in r.steps]
                row.scores = [ScoreRow(**_copy(s, _SCORE_COLS)) for s in r.scores]
                dest.add(row)
                dest.flush()  # gives the new result its id, for its labels
                for lab in labels_by_result.get(r.id, []):
                    dest.add(Label(result_id=row.id, **_copy(lab, _LABEL_COLS)))
            imported.append(run.id)
    source.dispose()
    return imported, skipped
