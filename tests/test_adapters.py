"""Scout and Gearbox adapters against fake HTTP servers (no network, no cost)."""

import json

import httpx
import pytest

from dyno.agents.gearbox import GearboxAgent
from dyno.agents.scout import ScoutAgent, ScoutError, render, to_steps

SCOUT_STEPS = [
    {
        "i": 1,
        "node": "researcher",
        "kind": "tool_call",
        "name": "web_search",
        "ok": True,
        "ms": 800,
        "input": '{"query": "NHS founded"}',
        "output": "[results]",
    },
    {
        "i": 0,
        "node": "planner",
        "kind": "llm_call",
        "name": "claude-haiku-5-5",
        "ok": True,
        "ms": 1200,
        "input": "plan this",
        "output": "{...}",
        "tokens_in": 100,
        "tokens_out": 20,
        "cost_gbp": 0.001,
    },
    {
        "i": 2,
        "node": "reader",
        "kind": "tool_call",
        "name": "fetch_url",
        "ok": False,
        "ms": 30,
        "input": "not json",
        "output": None,
        "error": "403",
    },
]

REPORT = {
    "summary": "The NHS began in 1948.",
    "sections": [
        {
            "heading": "Founding",
            "claims": [
                {"text": "Launched 5 July 1948.", "source_ids": ["S1"], "verdict": "supported"},
                {"text": "Led by Bevan.", "source_ids": ["S2"], "verdict": "unsupported"},
            ],
        }
    ],
    "limitations": ["Only two sources."],
    "stop_reason": None,
}


class FakeScout:
    """Just enough of Scout's API: auth, documents, research jobs, trajectory."""

    def __init__(self, status="complete", busy=0, polls=1, docs_after=1):
        self.status, self.busy, self.polls, self.docs_after = status, busy, polls, docs_after
        self.calls: list[tuple[str, str]] = []
        self.uploaded: list[str] = []
        self.doc_polls = 0
        self.token = "t1"

    def __call__(self, req: httpx.Request) -> httpx.Response:
        path, method = req.url.path, req.method
        self.calls.append((method, path))
        if path == "/auth/register":
            return httpx.Response(201, json={"id": "u"})
        if path == "/auth/login":
            return httpx.Response(200, json={"access_token": self.token, "expires_in": 3600})
        if req.headers.get("Authorization") != f"Bearer {self.token}":
            return httpx.Response(401, json={"detail": "expired"})
        if path == "/documents" and method == "POST":
            self.uploaded.append(req.content.split(b'filename="')[1].split(b'"')[0].decode())
            return httpx.Response(202, json={})
        if path == "/documents":
            self.doc_polls += 1
            status = "ready" if self.doc_polls >= self.docs_after else "processing"
            return httpx.Response(
                200, json=[{"filename": f, "status": status} for f in self.uploaded]
            )
        if path == "/research" and method == "POST":
            assert json.loads(req.content) == {
                "question": "When was the NHS founded?",
                "use_web": True,
                "use_docs": True,
            }
            if self.busy:
                self.busy -= 1
                return httpx.Response(429, headers={"Retry-After": "5"}, json={"detail": "busy"})
            return httpx.Response(202, json={"job_id": "j1", "status": "queued"})
        if path == "/research/j1":
            self.polls -= 1
            status = "running" if self.polls > 0 else self.status
            job = {"status": status, "cost_gbp": 0.03, "error": None, "report": None}
            if status == "complete":
                job["report"] = REPORT
            if status == "failed":
                job["error"] = "budget"
            return httpx.Response(200, json=job)
        if path == "/research/j1/trajectory":
            return httpx.Response(
                200,
                json={
                    "steps": SCOUT_STEPS,
                    "sources": [{"id": "S1", "title": "NHS", "url_or_doc": "https://nhs.uk"}],
                    "claims": [{"section": "Founding", "text": "Launched 5 July 1948."}],
                },
            )
        return httpx.Response(404, json={"detail": f"no route {path}"})


def scout(fake: FakeScout, **kw) -> tuple[ScoutAgent, list[float]]:
    sleeps: list[float] = []
    agent = ScoutAgent(
        "http://scout.test", transport=httpx.MockTransport(fake), sleep=sleeps.append, **kw
    )
    return agent, sleeps


def test_scout_run_maps_report_and_trajectory():
    fake = FakeScout(polls=3)
    agent, sleeps = scout(fake)
    result = agent.run("When was the NHS founded?")
    assert result.error is None
    assert result.final_answer.startswith("The NHS began in 1948.")
    assert "- [not supported by source] Led by Bevan. [S2]" in result.final_answer
    assert [(s.type, s.name) for s in result.steps] == [
        ("llm_call", "claude-haiku-5-5"),
        ("tool_call", "web_search"),
        ("tool_result", "web_search"),
        ("tool_call", "fetch_url"),
        ("tool_result", "fetch_url"),
    ]
    assert result.metadata["job_id"] == "j1" and result.metadata["sources"][0]["id"] == "S1"
    assert len(sleeps) == 2  # polled while running


def test_to_steps_details():
    llm, call, ok, bad_call, bad = to_steps(SCOUT_STEPS)
    assert (llm.input_tokens, llm.output_tokens, llm.cost_gbp) == (100, 20, 0.001)
    assert llm.args["node"] == "planner"
    assert call.args == {"query": "NHS founded"}
    assert ok.output == "[results]" and ok.args == {"ok": True}
    assert bad_call.args == {"input": "not json"}  # cut or non-JSON input kept as text
    assert bad.output == "403" and bad.args == {"ok": False}


def test_render_without_sections():
    assert render({"summary": "No evidence found."}) == "No evidence found."
    assert "## Limitations" in render(REPORT)


def test_scout_failed_job_is_an_agent_error():
    agent, _ = scout(FakeScout(status="failed"))
    result = agent.run("When was the NHS founded?")
    assert result.error == "Scout job failed: budget"
    assert len(result.steps) == 5  # the trajectory so far is still kept


def test_scout_waits_out_429():
    fake = FakeScout(busy=2)
    agent, sleeps = scout(fake)
    assert agent.run("When was the NHS founded?").error is None
    assert sleeps[:2] == [5.0, 5.0]


def test_scout_logs_in_again_when_token_expires():
    fake = FakeScout()
    agent, _ = scout(fake)
    fake.token = "t2"  # server-side expiry: old token now gets 401
    assert agent.run("When was the NHS founded?").error is None
    assert fake.calls.count(("POST", "/auth/login")) == 2


def test_scout_timeout(monkeypatch):
    agent, _ = scout(FakeScout(polls=10**6), timeout_s=0)
    with pytest.raises(ScoutError, match="still running"):
        agent.run("When was the NHS founded?")


def test_scout_uploads_corpus_and_waits(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 a")
    (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4 b")
    fake = FakeScout(docs_after=3)
    _agent, sleeps = scout(fake, corpus_dir=tmp_path)
    assert fake.uploaded == ["a.pdf", "b.pdf"]
    assert len(sleeps) == 2


def test_scout_unreachable():
    def refuse(req):
        raise httpx.ConnectError("refused")

    with pytest.raises(ScoutError, match="can't reach Scout"):
        ScoutAgent("http://scout.test", transport=httpx.MockTransport(refuse))


# --- Gearbox ---


def gearbox_server(status=200):
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        body = json.loads(req.content)
        assert body["model"] == "auto" and body["messages"][0]["content"] == "17 x 23?"
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "over budget"}})
        return httpx.Response(
            200,
            headers={
                "x-gearbox-tier": "M",
                "x-gearbox-model": "anthropic/claude-haiku-5-5",
                "x-gearbox-cost": "0.000120",
                "x-gearbox-router": "v3",
                "x-gearbox-cache": "miss",
                "x-gearbox-reason": "reasoning",
            },
            json={
                "model": "x",
                "choices": [{"message": {"content": "391"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 3},
            },
        )

    return httpx.MockTransport(handler)


def test_gearbox_maps_headers_to_step():
    result = GearboxAgent("http://gb.test", transport=gearbox_server()).run("17 x 23?")
    assert result.final_answer == "391"
    (step,) = result.steps
    assert (step.name, step.cost_gbp, step.input_tokens) == (
        "anthropic/claude-haiku-5-5",
        0.00012,
        12,
    )
    assert step.args == {"tier": "M", "router": "v3"}
    assert result.metadata["reason"] == "reasoning" and result.metadata["finish_reason"] == "stop"


def test_gearbox_http_error_is_agent_error():
    result = GearboxAgent("http://gb.test", transport=gearbox_server(429)).run("17 x 23?")
    assert result.error == "HTTP 429: over budget"


def test_gearbox_unreachable():
    def refuse(req):
        raise httpx.ConnectError("refused")

    with pytest.raises(RuntimeError, match="can't reach Gearbox"):
        GearboxAgent("http://gb.test", transport=httpx.MockTransport(refuse))
