"""Tables: runs -> cases (a snapshot per run) -> results (one per case attempt) -> steps
and scores (one per result and scorer).

Cases are copied into every run rather than shared, because case files get edited:
`compare` must judge each run against the cases it actually ran.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Fixed constraint names, so later migrations can alter them on SQLite and Postgres alike.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    suite: Mapped[str] = mapped_column(String(200))
    agent: Mapped[str] = mapped_column(String(200))
    k: Mapped[int]
    git_commit: Mapped[str | None] = mapped_column(String(40))
    git_dirty: Mapped[bool | None]
    config_hash: Mapped[str] = mapped_column(String(64), index=True)
    dyno_version: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # running | finished | interrupted
    status: Mapped[str] = mapped_column(String(20))
    # The suite's scorer specs, so `dyno score` re-scores with the same settings.
    # None (runs from before M2) = the default deterministic scorers.
    scorers: Mapped[list[Any] | None] = mapped_column(JSON)

    cases: Mapped[list[RunCase]] = relationship(back_populates="run", cascade="all, delete")
    results: Mapped[list[Result]] = relationship(
        back_populates="run", cascade="all, delete", order_by="Result.id"
    )


class RunCase(Base):
    __tablename__ = "cases"

    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    input: Mapped[str] = mapped_column(Text)
    expected: Mapped[Any] = mapped_column(JSON, nullable=True)
    must_call: Mapped[list[str]] = mapped_column(JSON)
    must_not_call: Mapped[list[str]] = mapped_column(JSON)
    max_steps: Mapped[int | None]
    tags: Mapped[list[str]] = mapped_column(JSON)
    sources: Mapped[list[str]] = mapped_column(JSON)
    # Column names avoid MATCH and CHECK, which are SQL keywords.
    match: Mapped[str | None] = mapped_column("match_mode", String(10))
    check: Mapped[str | None] = mapped_column("check_fn", String(200))

    run: Mapped[Run] = relationship(back_populates="cases")


class Result(Base):
    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint("run_id", "case_id", "attempt"),
        ForeignKeyConstraint(
            ["run_id", "case_id"], ["cases.run_id", "cases.case_id"], ondelete="CASCADE"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[str] = mapped_column(String(200))
    attempt: Mapped[int]  # 1..k
    final_answer: Mapped[str] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[float]  # wall clock around agent.run, measured by Dyno
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    cost_gbp: Mapped[float | None]
    n_steps: Mapped[int]
    meta: Mapped[dict[str, Any]] = mapped_column(JSON)  # AgentResult.metadata
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    run: Mapped[Run] = relationship(back_populates="results")
    steps: Mapped[list[StepRow]] = relationship(
        back_populates="result", cascade="all, delete", order_by="StepRow.idx"
    )
    scores: Mapped[list[ScoreRow]] = relationship(
        back_populates="result", cascade="all, delete-orphan", order_by="ScoreRow.id"
    )


class StepRow(Base):
    __tablename__ = "steps"
    __table_args__ = (UniqueConstraint("result_id", "idx"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("results.id", ondelete="CASCADE"))
    idx: Mapped[int]  # 0-based order within the attempt
    type: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))
    args: Mapped[dict[str, Any]] = mapped_column(JSON)
    output: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    cost_gbp: Mapped[float | None]
    latency_ms: Mapped[float | None]

    result: Mapped[Result] = relationship(back_populates="steps")


class ScoreRow(Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("result_id", "scorer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("results.id", ondelete="CASCADE"))
    scorer: Mapped[str] = mapped_column(String(50))
    score: Mapped[float | None]
    passed: Mapped[bool | None]
    explanation: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSON)

    result: Mapped[Result] = relationship(back_populates="scores")


class Label(Base):
    """A human's verdict on one judged thing, for calibrating the judge against."""

    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("result_id", "scorer", "item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("results.id", ondelete="CASCADE"))
    scorer: Mapped[str] = mapped_column(String(50))  # the judge this label checks
    # "" for a whole-answer label; the claim's text for a hallucination claim label.
    item: Mapped[str] = mapped_column(Text, default="")
    label: Mapped[bool | None]  # None = the labeller was unsure
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    result: Mapped[Result] = relationship()
