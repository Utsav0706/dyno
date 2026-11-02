"""What to hand-label, and how to show it (`dyno label`).

Two kinds of item:
- task: one whole answer. The labeller decides task success and quality (>= 4/5).
- claim: one factual claim the hallucination judge checked, with the evidence that
  bears on it. The labeller decides whether that evidence supports it. Labels are
  per claim, not per answer: almost every answer passes the hallucination check, so
  per-answer labels would leave kappa with nothing to measure, and no one can check a
  whole answer against 300,000 characters of evidence by eye.

Labelling is blind: the judge's verdict is never shown. The sample is drawn with a
fixed seed (same order every time, so a session can stop and resume), and it takes
every item the judge failed plus a random share of the rest, so both verdicts are
well represented; the calibration report says so.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from dyno.cases import Case
from dyno.scoring.base import parse_spec
from dyno.scoring.judges import Hallucination
from dyno.store.db import Store, attempt_from_row, case_from_row
from dyno.store.models import Label, Result, Run

SEED = 7
EXCERPT_CHARS = 700


@dataclass
class TaskItem:
    result_id: int
    run_id: str
    case_id: str
    attempt: int
    question: str
    key: str  # numbered key points, or the unanswerable note
    answer: str


@dataclass
class ClaimItem:
    result_id: int
    run_id: str
    case_id: str
    attempt: int
    claim: str
    excerpts: list[str]  # the passage the judge cited, or the closest matches


def _runs(store: Store, run_ids: list[str] | None) -> list[Run]:
    with Session(store.engine) as s:
        ids = run_ids or list(s.scalars(select(Run.id).order_by(Run.started_at)))
    runs = [store.get_run(i) for i in ids]
    missing = [i for i, r in zip(ids, runs, strict=True) if r is None]
    if missing:
        raise LookupError(f"no runs {missing}")
    return [r for r in runs if r is not None]


def _labelled(store: Store, scorer: str) -> set[tuple[int, str]]:
    with Session(store.engine) as s:
        rows = s.execute(select(Label.result_id, Label.item).where(Label.scorer == scorer))
        return {(r, i) for r, i in rows}


def _sample[T](fails: list[T], passes: list[T], n: int) -> list[T]:
    rng = random.Random(SEED)
    picked = fails[:n] + rng.sample(passes, max(0, min(len(passes), n - len(fails))))
    rng.shuffle(picked)  # order mustn't give away which ones the judge failed
    return picked


def _key(case: Case) -> str:
    points = [case.expected] if isinstance(case.expected, str) else (case.expected or [])
    if points:
        return "\n".join(f"  {i}. {p}" for i, p in enumerate(points, start=1))
    if "unanswerable" in case.tags:
        return "  UNANSWERABLE: the evidence needed does not exist or is not available."
    return "  (none)"


def task_items(store: Store, run_ids: list[str] | None, n: int) -> list[TaskItem]:
    """Answers the task judge scored, not yet labelled: all judge fails + random passes."""
    done = _labelled(store, "task_rubric")
    fails, passes = [], []
    for run in _runs(store, run_ids):
        cases = {c.case_id: case_from_row(c) for c in run.cases}
        for r in run.results:
            sc = next((s for s in r.scores if s.scorer == "task_rubric"), None)
            if sc is None or sc.passed is None or (r.id, "") in done:
                continue
            case = cases[r.case_id]
            item = TaskItem(
                r.id, run.id, r.case_id, r.attempt, case.input, _key(case), r.final_answer
            )
            (passes if sc.passed else fails).append(item)
    return _sample(fails, passes, n)


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9£.,%-]+", text.lower()) if len(w) > 2}


def excerpt(passage: str, claim: str, size: int = EXCERPT_CHARS) -> str:
    """The window of a long passage that shares the most words with the claim."""
    if len(passage) <= size:
        return passage
    want = _words(claim)
    best, best_at = -1, 0
    for start in range(0, len(passage) - size + 1, size // 4):
        hit = len(want & _words(passage[start : start + size]))
        if hit > best:
            best, best_at = hit, start
    return "..." + passage[best_at : best_at + size] + "..."


def _hallucination_scorer(run: Run) -> Hallucination:
    """The scorer with the settings the run used (e.g. exclude_tools), for its evidence."""
    for spec in run.scorers or []:
        name, params = parse_spec(spec)
        if name == "hallucination":
            return Hallucination(**params)
    return Hallucination()


def claim_items(store: Store, run_ids: list[str] | None, n: int) -> list[ClaimItem]:
    """Claims the hallucination judge checked, not yet labelled: all it called
    unsupported + random supported ones. Statements about the search are left out."""
    done = _labelled(store, "hallucination")
    fails, passes = [], []
    for run in _runs(store, run_ids):
        cases = {c.case_id: case_from_row(c) for c in run.cases}
        scorer = _hallucination_scorer(run)
        for r in run.results:
            sc = next((s for s in r.scores if s.scorer == "hallucination"), None)
            if sc is None or sc.passed is None:
                continue
            passages, _ = scorer.evidence(cases[r.case_id], attempt_from_row(r))
            for c in sc.details.get("claims", []):
                if c.get("meta") or (r.id, c["claim"]) in done:
                    continue
                cited = re.fullmatch(r"E(\d+)", c.get("evidence", "").strip())
                if cited and int(cited.group(1)) <= len(passages):
                    shown = [passages[int(cited.group(1)) - 1]]
                else:
                    want = _words(c["claim"])
                    shown = sorted(passages, key=lambda p: -len(want & _words(p)))[:3]
                item = ClaimItem(
                    r.id,
                    run.id,
                    r.case_id,
                    r.attempt,
                    c["claim"],
                    [excerpt(p, c["claim"]) for p in shown],
                )
                (passes if c["supported"] else fails).append(item)
    return _sample(fails, passes, n)


def save_label(
    store: Store, result_id: int, scorer: str, label: bool | None, item: str = "", note: str = ""
) -> None:
    from datetime import UTC, datetime

    with Session(store.engine) as s, s.begin():
        old = s.scalar(
            select(Label).where(
                Label.result_id == result_id, Label.scorer == scorer, Label.item == item
            )
        )
        if old is not None:
            old.label, old.note, old.created_at = label, note, datetime.now(UTC)
        else:
            s.add(
                Label(
                    result_id=result_id,
                    scorer=scorer,
                    item=item,
                    label=label,
                    note=note,
                    created_at=datetime.now(UTC),
                )
            )


def all_labels(store: Store) -> list[Label]:
    with Session(store.engine, expire_on_commit=False) as s:
        stmt = select(Label).options(
            selectinload(Label.result).selectinload(Result.scores),
        )
        return list(s.scalars(stmt))
