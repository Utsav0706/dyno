"""Scout (the research agent) over its HTTP API.

Setup, once per Dyno run (in __init__, so a Scout that's down or refuses us stops the
run before any case starts):
  register a fresh user (random email + password, kept in memory only) and log in;
  upload the PDFs in SCOUT_CORPUS_DIR, if set, and wait until they're searchable.
A fresh user per run means runs never see each other's documents or job limits.

One attempt:
  POST /research -> poll GET /research/{id} until it finishes -> GET .../trajectory.

Scout's trajectory maps onto Dyno steps: llm_call stays llm_call; each tool_call
becomes a tool_call (JSON input parsed into args) followed by a tool_result (its
output), the shape Dyno's tool and step scorers expect.
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from dyno.agent import AgentResult, Step
from dyno.config import get_settings

log = logging.getLogger(__name__)

TERMINAL = {"complete", "partial", "no_evidence", "failed"}  # Scout's jobs/runner.py
MAX_RETRY_WAIT_S = 120  # longest Retry-After we'll sit out on a 429 before giving up
VERDICT_FLAGS = {
    "unsupported": "[not supported by source] ",
    "contradicted": "[contradicted by source] ",
    "unverified": "[not checked] ",
}


class ScoutError(RuntimeError):
    pass


class ScoutAgent:
    def __init__(
        self,
        base_url: str | None = None,
        corpus_dir: Path | None = None,
        *,
        use_web: bool = True,
        use_docs: bool = True,
        timeout_s: float = 300.0,
        poll_s: float = 2.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        settings = get_settings()
        self.use_web, self.use_docs = use_web, use_docs
        self.timeout_s, self.poll_s, self.sleep = timeout_s, poll_s, sleep
        self.http = httpx.Client(
            base_url=base_url or settings.scout_url, transport=transport, timeout=60.0
        )
        self.email = f"dyno-{secrets.token_hex(6)}@example.com"
        self.password = secrets.token_urlsafe(24)
        self._register()
        self._login()
        corpus = corpus_dir or settings.scout_corpus_dir
        if corpus:
            self._upload_corpus(Path(corpus))

    # --- setup ---

    def _register(self) -> None:
        try:
            r = self.http.post(
                "/auth/register", json={"email": self.email, "password": self.password}
            )
        except httpx.ConnectError as exc:
            raise ScoutError(
                f"can't reach Scout at {self.http.base_url}: start it with "
                "`py scripts/dev_api.py` in the scout repo"
            ) from exc
        _ok(r, "register")

    def _login(self) -> None:
        r = self.http.post("/auth/login", json={"email": self.email, "password": self.password})
        token = _ok(r, "login")["access_token"]
        self.http.headers["Authorization"] = f"Bearer {token}"

    def _request(self, method: str, url: str, **kw: Any) -> httpx.Response:
        """One API call; logs in again once if the token expired (60-minute TTL)."""
        r = self.http.request(method, url, **kw)
        if r.status_code == 401:
            self._login()
            r = self.http.request(method, url, **kw)
        return r

    def _upload_corpus(self, directory: Path) -> None:
        pdfs = sorted(directory.glob("*.pdf"))
        if not pdfs:
            raise ScoutError(f"no PDFs in {directory}")
        for pdf in pdfs:
            files = {"file": (pdf.name, pdf.read_bytes(), "application/pdf")}
            _ok(self._request("POST", "/documents", files=files), f"upload {pdf.name}")
        deadline = time.monotonic() + self.timeout_s
        while True:
            docs = _ok(self._request("GET", "/documents"), "list documents")
            failed = [d["filename"] for d in docs if d["status"] == "failed"]
            if failed:
                raise ScoutError(f"Scout could not process: {failed}")
            if all(d["status"] == "ready" for d in docs):
                log.info("corpus ready", extra={"documents": len(docs)})
                return
            if time.monotonic() > deadline:
                raise ScoutError("corpus still processing after timeout")
            self.sleep(self.poll_s)

    # --- one attempt ---

    def run(self, input: str) -> AgentResult:
        job_id = self._start(input)
        job = self._wait(job_id)
        traj = _ok(self._request("GET", f"/research/{job_id}/trajectory"), "trajectory")
        steps = to_steps(traj["steps"])
        report = job.get("report") or {}
        metadata = {
            "job_id": job_id,
            "scout_status": job["status"],
            "stop_reason": report.get("stop_reason"),
            "scout_cost_gbp": job.get("cost_gbp"),
            "sources": traj.get("sources", []),
            "claims": traj.get("claims", []),
        }
        if job["status"] == "failed":
            error = f"Scout job failed: {job.get('error') or 'no reason given'}"
            return AgentResult(steps=steps, error=error, metadata=metadata)
        return AgentResult(final_answer=render(report), steps=steps, metadata=metadata)

    def _start(self, question: str) -> str:
        body = {"question": question, "use_web": self.use_web, "use_docs": self.use_docs}
        while True:
            r = self._request("POST", "/research", json=body)
            if r.status_code != 429:
                return _ok(r, "start research")["job_id"]
            # Job limits per user: wait as long as Scout asks, unless that's absurd.
            wait = float(r.headers.get("Retry-After", "30"))
            if wait > MAX_RETRY_WAIT_S:
                raise ScoutError(f"Scout rate limit: retry in {wait:.0f}s ({_detail(r)})")
            log.info("scout busy, waiting", extra={"seconds": wait})
            self.sleep(wait)

    def _wait(self, job_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_s
        while True:
            job = _ok(self._request("GET", f"/research/{job_id}"), "job status")
            if job["status"] in TERMINAL:
                return job
            if time.monotonic() > deadline:
                raise ScoutError(f"job {job_id} still {job['status']} after {self.timeout_s:.0f}s")
            self.sleep(self.poll_s)


def to_steps(scout_steps: list[dict[str, Any]]) -> list[Step]:
    steps: list[Step] = []
    for s in sorted(scout_steps, key=lambda s: s["i"]):
        if s["kind"] == "llm_call":
            args = {"node": s["node"], "input": s.get("input")}
            if not s["ok"]:
                args["error"] = s.get("error")
            steps.append(
                Step(
                    type="llm_call",
                    name=s["name"],
                    args=args,
                    output=s.get("output"),
                    input_tokens=s.get("tokens_in"),
                    output_tokens=s.get("tokens_out"),
                    cost_gbp=s.get("cost_gbp"),
                    latency_ms=s.get("ms"),
                )
            )
        else:
            steps.append(
                Step(
                    type="tool_call",
                    name=s["name"],
                    args=_parse_args(s.get("input")),
                    latency_ms=s.get("ms"),
                )
            )
            steps.append(
                Step(
                    type="tool_result",
                    name=s["name"],
                    args={"ok": s["ok"]},
                    output=s.get("output") if s["ok"] else (s.get("error") or s.get("output")),
                )
            )
    return steps


def _parse_args(raw: str | None) -> dict[str, Any]:
    """Tool inputs arrive as JSON text (cut at 4,000 chars); keep the raw text if cut."""
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except ValueError:
        return {"input": raw}
    return value if isinstance(value, dict) else {"input": value}


def render(report: dict[str, Any]) -> str:
    """The report as plain text: what a reader (or a judge) sees, minus the source list."""
    lines = [report.get("summary", "")]
    for section in report.get("sections", []):
        lines += ["", f"## {section['heading']}"]
        for claim in section["claims"]:
            flag = VERDICT_FLAGS.get(claim.get("verdict", ""), "")
            refs = "".join(f"[{sid}]" for sid in claim.get("source_ids", []))
            lines.append(f"- {flag}{claim['text']} {refs}".rstrip())
    if report.get("limitations"):
        lines += ["", "## Limitations"] + [f"- {item}" for item in report["limitations"]]
    return "\n".join(lines).strip()


def _detail(r: httpx.Response) -> str:
    try:
        return str(r.json().get("detail", r.text[:200]))
    except ValueError:
        return r.text[:200]


def _ok(r: httpx.Response, what: str) -> Any:
    if r.status_code >= 400:
        raise ScoutError(f"{what}: HTTP {r.status_code}: {_detail(r)}")
    return r.json()
