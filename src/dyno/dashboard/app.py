"""The Streamlit dashboard (`dyno dashboard`). Read-only: it never writes to the store.

Four views: every run with score trends, one run down to each step of each attempt,
two runs compared (with the gate), and saved failure clusters.
"""

from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from dyno.compare import compare_runs
from dyno.config import get_settings
from dyno.dashboard import data
from dyno.gate import gate
from dyno.report import Report, build_report
from dyno.store import Store, open_engine
from dyno.store.models import Run

VIEWS = ("Runs", "Run", "Compare", "Clusters")
PCT = st.column_config.NumberColumn(format="percent")
GBP = st.column_config.NumberColumn(format="%.4f")


@st.cache_resource
def get_store(url: str) -> Store:
    return Store(open_engine(url))


@st.cache_resource(max_entries=64)
def load(url: str, run_id: str, finished: str) -> tuple[Run, Report]:
    """A run and its report; `finished` in the key so a re-scored run reloads."""
    run = get_store(url).get_run(run_id)
    assert run is not None
    return run, build_report(run)


def run_label(run: Run) -> str:
    return f"{run.id}  {run.started_at:%Y-%m-%d %H:%M}  {run.suite} ({run.agent}, k={run.k})"


def open_run(key: str, ids: list[str]) -> None:
    """Dataframe click callback (runs before the rerun, so widget state may change)."""
    rows = st.session_state[key].selection.rows
    if rows:
        st.session_state.run_id = ids[rows[0]]
        st.session_state.view = "Run"
        st.session_state.pop("case_id", None)


def pick_case(key: str, ids: list[str]) -> None:
    rows = st.session_state[key].selection.rows
    st.session_state.case_id = ids[rows[0]] if rows else None


def runs_view(url: str, runs: list[Run]) -> None:
    reports = [load(url, r.id, str(r.finished_at))[1] for r in runs]
    st.subheader("Runs")
    st.caption("Click a row to open the run.")
    st.dataframe(
        pd.DataFrame([data.run_row(rep) for rep in reports]),
        hide_index=True,
        on_select=lambda: open_run("runs_table", [r.id for r in runs]),
        selection_mode="single-row",
        key="runs_table",
        column_config={
            "pass rate": PCT,
            "pass@k": PCT,
            "pass^k": PCT,
            "agent GBP": GBP,
            "judge GBP": GBP,
        },
    )

    st.subheader("Trends")
    suites = sorted({rep.suite for rep in reports})
    suite = st.selectbox("Suite", suites, suites.index(reports[0].suite))  # newest run's
    picked = [rep for rep in reports if rep.suite == suite]
    rows = data.trend_rows(picked)
    if len({rep.config_hash for rep in picked}) > 1:
        st.caption(
            "These runs used different cases or settings (e.g. a 10-case subset vs all 50), "
            "so points are not all like-for-like. Compare two runs for a fair comparison."
        )
    if rows:
        # Altair rather than st.line_chart: that one zooms on scroll, hijacking the page.
        chart = (
            alt.Chart(pd.DataFrame(rows))
            .mark_line(point=True)
            .encode(
                x=alt.X("run:N", sort=None, title=None),
                y=alt.Y("pass rate:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
                color=alt.Color("metric:N", title=None),
                tooltip=["run", "metric", alt.Tooltip("pass rate:Q", format=".0%")],
            )
        )
        st.altair_chart(chart)


def run_view(url: str, runs: list[Run]) -> None:
    by_id = {r.id: r for r in runs}
    if st.session_state.get("run_id") not in by_id:
        st.session_state.run_id = runs[0].id
    run_id = st.selectbox(
        "Run", list(by_id), format_func=lambda i: run_label(by_id[i]), key="run_id"
    )
    run, rep = load(url, run_id, str(by_id[run_id].finished_at))

    cols = st.columns(5)
    cols[0].metric("Attempt pass rate", _pct(rep.attempt_pass_rate))
    cols[1].metric(f"pass@{rep.k}", _pct(rep.pass_at_k))
    cols[2].metric(f"pass^{rep.k}", _pct(rep.pass_hat_k))
    cols[3].metric("Agent cost", "n/a" if rep.cost_gbp is None else f"GBP {rep.cost_gbp:.2f}")
    cols[4].metric(
        "Median time", "n/a" if rep.latency_p50_s is None else f"{rep.latency_p50_s:.0f}s"
    )

    left, right = st.columns(2)
    left.markdown("**Scorers**")
    left.dataframe(
        pd.DataFrame(data.scorer_rows(rep)),
        hide_index=True,
        column_config={
            "pass rate": PCT,
            "mean score": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    right.markdown("**By tag**")
    if rep.tags:
        right.dataframe(
            pd.DataFrame(data.tag_rows(rep)), hide_index=True, column_config={"pass rate": PCT}
        )
    else:
        right.caption("No tags.")
    if rep.flaky:
        st.markdown("**Flaky:** " + ", ".join(f"`{c}`" for c in rep.flaky))

    st.subheader("Cases")
    st.caption("Click a case to see every attempt, step and score.")
    cases = data.case_rows(run, rep)
    ids = [c["case"] for c in cases]
    status = st.multiselect("Status", ["pass", "flaky", "fail", "n/a"], key="status_filter")
    shown = [c for c in cases if not status or c["status"] in status]
    shown_ids = [c["case"] for c in shown]
    table_key = f"cases_{run.id}_{'-'.join(status)}"
    st.dataframe(
        pd.DataFrame(shown, columns=list(cases[0]) if cases else None),
        hide_index=True,
        on_select=lambda: pick_case(table_key, shown_ids),
        selection_mode="single-row",
        key=table_key,
    )
    case_id = st.session_state.get("case_id")
    if case_id in ids:
        case_view(run, case_id)


def case_view(run: Run, case_id: str) -> None:
    case = next(c for c in run.cases if c.case_id == case_id)
    st.subheader(f"Case `{case_id}`")
    st.markdown(f"**Input:** {case.input}")
    if case.expected is not None:
        st.markdown(f"**Expected:** {case.expected}")
    attempts = data.attempts_of(run, case_id)
    marks = {True: "pass", False: "fail", None: "n/a"}
    tabs = st.tabs([f"Attempt {r.attempt}: {marks[data.attempt_outcome(r)]}" for r in attempts])
    for tab, result in zip(tabs, attempts, strict=True):
        with tab:
            cost = "n/a" if result.cost_gbp is None else f"GBP {result.cost_gbp:.4f}"
            st.caption(f"{result.n_steps} steps, {result.latency_ms / 1000:.1f}s, {cost}")
            if result.error:
                st.error(result.error)
            st.markdown("**Answer**")
            st.text(result.final_answer or "(empty)")
            st.markdown("**Scores**")
            for sc in result.scores:
                mark = {True: "PASS", False: "FAIL", None: "n/a"}[sc.passed]
                score = "" if sc.score is None else f" ({sc.score:.2f})"
                with st.expander(f"{mark} {sc.scorer}{score}: {sc.explanation[:150]}"):
                    st.write(sc.explanation)
                    if sc.details:
                        st.json(sc.details, expanded=False)
            st.markdown("**Trajectory**")
            steps = data.step_rows(result)
            if not steps:
                st.caption("No steps recorded.")
                continue
            st.dataframe(pd.DataFrame(steps), hide_index=True)
            idx = st.number_input(
                "Show one step in full", 0, len(steps) - 1, 0, key=f"step_{result.id}"
            )
            step = result.steps[int(idx)]
            st.markdown(f"`{step.type}` **{step.name}**")
            st.code(json.dumps(step.args, indent=2, ensure_ascii=False), language="json")
            st.text(step.output or "(no output)")


def compare_view(url: str, runs: list[Run]) -> None:
    by_id = {r.id: r for r in runs}
    ids = list(by_id)
    if len(ids) < 2:
        st.info("Needs at least two runs.")
        return
    a_col, b_col = st.columns(2)
    a = a_col.selectbox("Baseline (A)", ids, 1, format_func=lambda i: run_label(by_id[i]))
    b = b_col.selectbox("Candidate (B)", ids, 0, format_func=lambda i: run_label(by_id[i]))
    run_a = load(url, a, str(by_id[a].finished_at))[0]
    run_b = load(url, b, str(by_id[b].finished_at))[0]
    c = compare_runs(run_a, run_b)
    note = "" if c.same_config else " Different configs: only shared cases count."
    st.caption(f"Compared on {c.common_cases} shared cases.{note}")
    st.dataframe(
        pd.DataFrame(
            [
                {"metric": m.metric, "A": m.a, "B": m.b, "change (pts)": m.delta_pp}
                for m in c.metrics
            ]
        ),
        hide_index=True,
        column_config={
            "A": PCT,
            "B": PCT,
            "change (pts)": st.column_config.NumberColumn(format="%+.1f"),
        },
    )
    cols = st.columns(3)
    for col, title, items in zip(
        cols,
        ("Newly failing", "Newly flaky", "Newly passing"),
        (c.newly_failing, c.newly_flaky, c.newly_passing),
        strict=True,
    ):
        col.markdown(f"**{title} ({len(items)})**")
        col.markdown("\n".join(f"- `{i}`" for i in items) or "None.")

    st.subheader("Gate")
    g1, g2, g3 = st.columns(3)
    metric = g1.selectbox("Metric", [m.metric for m in c.metrics])
    max_drop = g2.number_input("Max drop (pts)", 0.0, 100.0, 2.0, 0.5)
    strict = g3.checkbox("No new failures")
    result = gate(
        b, a, max_drop=max_drop, metric=metric, no_new_failures=strict, store=get_store(url)
    )
    (st.success if result.passed else st.error)(
        f"{'PASS' if result.passed else 'FAIL'}: {result.reason}"
    )


def clusters_view() -> None:
    folder = Path(st.text_input("Folder with `dyno cluster --format json` files", "reports"))
    found = data.load_clusterings(folder) if folder.is_dir() else []
    if not found:
        st.info(
            f"No cluster files in {folder}. Make one with: "
            f"dyno cluster RUN --format json --out {folder}/clusters.json"
        )
        return
    path = st.selectbox("File", [p for p, _ in found], format_func=lambda p: p.name)
    cl = dict(found)[path]
    sil = "n/a" if cl.silhouette is None else f"{cl.silhouette:.2f}"
    st.caption(
        f"Runs {', '.join(cl.run_ids)}: {cl.failures} failed attempts in {cl.k} clusters "
        f"(silhouette {sil})."
    )
    for c in cl.clusters:
        with st.expander(f"{c.name}: {c.share:.0%} ({c.size})"):
            st.markdown("Cases: " + ", ".join(f"`{i}`" for i in c.case_ids))
            for e in c.examples:
                st.markdown(f"- {' '.join(e.split())}")


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def main() -> None:
    st.set_page_config(page_title="Dyno", layout="wide")
    url = get_settings().database_url
    runs = get_store(url).list_runs()
    st.sidebar.title("Dyno")
    view = st.sidebar.radio("View", VIEWS, key="view")
    st.sidebar.caption(f"Store: {url}")
    if view == "Clusters":
        clusters_view()
    elif not runs:
        st.info("No runs yet. Try: dyno run examples/example_suite.yaml --k 3")
    elif view == "Runs":
        runs_view(url, runs)
    elif view == "Run":
        run_view(url, runs)
    else:
        compare_view(url, runs)


main()
