"""Group a run's failures by what went wrong (`dyno cluster`).

Each failed attempt becomes one text: the explanations of the scorers it failed. The
texts are embedded locally (BAAI/bge-small-en-v1.5, the model Scout and Gearbox use:
free, nothing leaves the machine), grouped with k-means, k chosen by silhouette score,
and each group gets a one-line name from the judge model (about GBP 0.001 per group).

Needs the optional extra: pip install -e ".[cluster]" (sentence-transformers and
scikit-learn; torch is large, and only this command uses it).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel

from dyno.judge import Judge, get_judge, load_prompt
from dyno.store.models import Run

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
MAX_K = 8  # and at most sqrt(failures): with few failures, a high k splits by question
NAME_EXAMPLES = 12  # explanations shown to the namer per cluster


class Embedder(Protocol):
    def __call__(self, texts: list[str]) -> Sequence[Sequence[float]]: ...


class FailedAttempt(BaseModel):
    run_id: str
    case_id: str
    attempt: int
    text: str


class Cluster(BaseModel):
    name: str
    size: int
    share: float  # of all failures
    case_ids: list[str]
    examples: list[str]


class Clustering(BaseModel):
    run_ids: list[str]
    failures: int
    k: int
    silhouette: float | None
    clusters: list[Cluster]
    judge_cost_gbp: float


class ClusterName(BaseModel):
    name: str


def failed_attempts(runs: list[Run], scorer: str | None = None) -> list[FailedAttempt]:
    out = []
    for run in runs:
        for r in run.results:
            failed = [
                s for s in r.scores if s.passed is False and (scorer is None or s.scorer == scorer)
            ]
            if r.error and scorer is None:
                text = f"agent error: {r.error}"
            elif failed:
                text = " | ".join(f"{s.scorer}: {s.explanation}" for s in failed)
            else:
                continue
            out.append(
                FailedAttempt(run_id=run.id, case_id=r.case_id, attempt=r.attempt, text=text)
            )
    return out


def local_embedder() -> Embedder:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError('clustering needs the extra: pip install -e ".[cluster]"') from exc
    model = SentenceTransformer(EMBED_MODEL)

    def embed(texts: list[str]) -> Sequence[Sequence[float]]:
        return model.encode(texts, normalize_embeddings=True).tolist()

    return embed


def choose_k(vectors: Sequence[Sequence[float]]) -> tuple[list[int], float | None]:
    """K-means labels for the k (2..MAX_K) with the best silhouette score."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    n = len(vectors)
    if n < 3:
        return [0] * n, None
    best: tuple[float, list[int]] | None = None
    for k in range(2, min(MAX_K, n - 1, max(2, math.ceil(math.sqrt(n)))) + 1):
        labels = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(vectors)
        if len(set(labels)) < 2:
            continue
        score = float(silhouette_score(vectors, labels))
        if best is None or score > best[0]:
            best = (score, [int(x) for x in labels])
    if best is None:
        return [0] * n, None
    return best[1], best[0]


def cluster_failures(
    runs: list[Run],
    *,
    scorer: str | None = None,
    embed: Embedder | None = None,
    judge: Judge | None = None,
) -> Clustering:
    items = failed_attempts(runs, scorer)
    if not items:
        return Clustering(
            run_ids=[r.id for r in runs],
            failures=0,
            k=0,
            silhouette=None,
            clusters=[],
            judge_cost_gbp=0.0,
        )
    vectors = (embed or local_embedder())([i.text for i in items])
    labels, silhouette = choose_k(vectors)
    judge = judge or get_judge()
    spent_before = judge.spent_gbp
    prompt = load_prompt("cluster_name_v1")

    clusters = []
    for label in sorted(set(labels)):
        members = [i for i, lab in zip(items, labels, strict=True) if lab == label]
        sample = [m.text[:400] for m in members[:NAME_EXAMPLES]]
        verdict = judge.ask(
            prompt,
            "<explanations>\n" + "\n\n".join(f"- {t}" for t in sample) + "\n</explanations>",
            ClusterName,
        )
        clusters.append(
            Cluster(
                name=verdict.parsed.name.strip(),
                size=len(members),
                share=len(members) / len(items),
                case_ids=sorted({m.case_id for m in members}),
                examples=sample[:3],
            )
        )
    clusters.sort(key=lambda c: -c.size)
    return Clustering(
        run_ids=[r.id for r in runs],
        failures=len(items),
        k=len(clusters),
        silhouette=silhouette,
        clusters=clusters,
        judge_cost_gbp=judge.spent_gbp - spent_before,
    )


def to_markdown(c: Clustering) -> str:
    sil = "n/a" if c.silhouette is None else f"{c.silhouette:.2f}"
    lines = [
        f"# Failure clusters: {', '.join(f'`{r}`' for r in c.run_ids)}",
        "",
        f"{c.failures} failed attempts in {c.k} clusters (silhouette {sil}; "
        f"naming cost GBP {c.judge_cost_gbp:.4f}).",
        "",
    ]
    lines += [
        f"- **{cl.name}** - {cl.share:.0%} of failures ({cl.size}) - "
        + ", ".join(f"`{i}`" for i in cl.case_ids[:6])
        + (" ..." if len(cl.case_ids) > 6 else "")
        for cl in c.clusters
    ]
    for cl in c.clusters:
        lines += ["", f"## {cl.name}", ""]
        lines += [f"- {' '.join(e.split())}" for e in cl.examples]
    return "\n".join(lines) + "\n"
