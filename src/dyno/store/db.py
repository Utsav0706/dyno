"""Open the database and write runs to it.

`open_engine` brings the schema up to date with Alembic every time, so `pip install`
then `dyno run` works with no separate setup step, and an old dyno.db is upgraded
in place when a later milestone adds a migration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import Session, selectinload

from dyno.agent import AgentResult, Step
from dyno.cases import Case, ScorerSpec
from dyno.scoring.base import Attempt, Score
from dyno.store.models import Result, Run, RunCase, ScoreRow, StepRow

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"


def alembic_config(url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def open_engine(url: str) -> Engine:
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":
        # SQLite ignores foreign keys (and ON DELETE CASCADE) unless asked, per connection.
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record) -> None:  # type: ignore[no-untyped-def]
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    cfg = alembic_config(url)
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
    return engine


def _now() -> datetime:
    return datetime.now(UTC)


class Store:
    """The few writes and reads the runner and CLI need. Reports and compare (M2, M7)
    read the same tables."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def start_run(
        self,
        *,
        run_id: str,
        suite: str,
        agent: str,
        k: int,
        git_commit: str | None,
        git_dirty: bool | None,
        config_hash: str,
        dyno_version: str,
        cases: list[Case],
        scorers: list[ScorerSpec],
    ) -> None:
        with Session(self.engine) as s, s.begin():
            run = Run(
                id=run_id,
                suite=suite,
                agent=agent,
                k=k,
                git_commit=git_commit,
                git_dirty=git_dirty,
                config_hash=config_hash,
                dyno_version=dyno_version,
                started_at=_now(),
                status="running",
                scorers=scorers,
            )
            run.cases = [RunCase(case_id=c.id, **c.model_dump(exclude={"id"})) for c in cases]
            s.add(run)

    def save_result(
        self,
        *,
        run_id: str,
        case_id: str,
        attempt: int,
        result: AgentResult,
        latency_ms: float,
        started_at: datetime,
        scores: dict[str, Score] | None = None,
    ) -> int:
        """Store one attempt (and its scores) in one transaction; returns the result id."""
        steps = result.steps

        def total(field: str) -> int | float | None:
            values = [getattr(st, field) for st in steps if getattr(st, field) is not None]
            return sum(values) if values else None

        with Session(self.engine) as s, s.begin():
            row = Result(
                run_id=run_id,
                case_id=case_id,
                attempt=attempt,
                final_answer=result.final_answer,
                error=result.error,
                latency_ms=latency_ms,
                input_tokens=total("input_tokens"),
                output_tokens=total("output_tokens"),
                cost_gbp=total("cost_gbp"),
                n_steps=len(steps),
                meta=result.metadata,
                started_at=started_at,
            )
            row.steps = [StepRow(idx=i, **st.model_dump()) for i, st in enumerate(steps)]
            row.scores = _score_rows(scores or {})
            s.add(row)
            s.flush()
            return row.id

    def replace_scores(self, result_id: int, scores: dict[str, Score]) -> None:
        """Swap in new scores for the scorers given; other scorers' rows stay."""
        with Session(self.engine) as s, s.begin():
            row = s.get_one(Result, result_id)
            row.scores = [sc for sc in row.scores if sc.scorer not in scores]
            s.flush()  # delete replaced rows before inserting, or the unique key clashes
            row.scores.extend(_score_rows(scores))

    def finish_run(self, run_id: str, status: str = "finished") -> None:
        with Session(self.engine) as s, s.begin():
            run = s.get_one(Run, run_id)
            run.status = status
            run.finished_at = _now()

    def list_runs(self) -> list[Run]:
        """Every run, newest first, without cases or results (cheap; for listings)."""
        with Session(self.engine, expire_on_commit=False) as s:
            return list(s.scalars(select(Run).order_by(Run.started_at.desc())))

    def get_run(self, run_id: str) -> Run | None:
        """A run with its cases, results and steps loaded (usable after the session)."""
        with Session(self.engine, expire_on_commit=False) as s:
            stmt = (
                select(Run)
                .where(Run.id == run_id)
                .options(
                    selectinload(Run.cases),
                    selectinload(Run.results).selectinload(Result.steps),
                    selectinload(Run.results).selectinload(Result.scores),
                )
            )
            return s.scalars(stmt).one_or_none()


def _score_rows(scores: dict[str, Score]) -> list[ScoreRow]:
    return [ScoreRow(scorer=name, **sc.model_dump()) for name, sc in scores.items()]


def case_from_row(row: RunCase) -> Case:
    return Case(
        id=row.case_id,
        input=row.input,
        expected=row.expected,
        must_call=row.must_call,
        must_not_call=row.must_not_call,
        max_steps=row.max_steps,
        tags=row.tags,
        sources=row.sources,
        match=row.match,  # type: ignore[arg-type]
        check=row.check,
    )


def attempt_from_row(row: Result) -> Attempt:
    steps = [
        Step(
            type=st.type,  # type: ignore[arg-type]
            name=st.name,
            args=st.args,
            output=st.output,
            input_tokens=st.input_tokens,
            output_tokens=st.output_tokens,
            cost_gbp=st.cost_gbp,
            latency_ms=st.latency_ms,
        )
        for st in row.steps
    ]
    return Attempt(
        final_answer=row.final_answer, steps=steps, error=row.error, latency_ms=row.latency_ms
    )
