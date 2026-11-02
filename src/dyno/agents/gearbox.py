"""Gearbox (the LLM router) over its OpenAI-compatible API.

One attempt is one POST /v1/chat/completions with model "auto", so Gearbox picks the
model. It becomes a single llm_call step; Gearbox's x-gearbox-* headers give the model
that answered, the cost in GBP and why it was routed there.
"""

from __future__ import annotations

import time

import httpx

from dyno.agent import AgentResult, Step
from dyno.config import get_settings

TIMEOUT_S = 300.0  # a long answer from the large tier can take a couple of minutes


class GearboxAgent:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        model: str = "auto",
        max_tokens: int | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model, self.max_tokens = model, max_tokens
        self.http = httpx.Client(
            base_url=base_url or get_settings().gearbox_url, transport=transport, timeout=TIMEOUT_S
        )
        # Fail before the run starts, not once per case, if Gearbox isn't up.
        try:
            self.http.get("/health").raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"can't reach Gearbox at {self.http.base_url}/health: {exc}. Start it with "
                "`py -m gearbox.service` in the gearbox repo"
            ) from exc

    def run(self, input: str) -> AgentResult:
        body: dict[str, object] = {
            "model": self.model,
            "messages": [{"role": "user", "content": input}],
        }
        if self.max_tokens:
            body["max_tokens"] = self.max_tokens
        start = time.perf_counter()
        r = self.http.post("/v1/chat/completions", json=body)
        ms = (time.perf_counter() - start) * 1000
        if r.status_code != 200:
            try:
                message = r.json()["error"]["message"]
            except (ValueError, KeyError, TypeError):
                message = r.text[:300]
            return AgentResult(error=f"HTTP {r.status_code}: {message}")

        data = r.json()
        h = r.headers
        answer = data["choices"][0]["message"]["content"] or ""
        model = h.get("x-gearbox-model", data.get("model", ""))
        cost = h.get("x-gearbox-cost")
        step = Step(
            type="llm_call",
            name=model,
            args={"tier": h.get("x-gearbox-tier"), "router": h.get("x-gearbox-router")},
            output=answer,
            input_tokens=data["usage"]["prompt_tokens"],
            output_tokens=data["usage"]["completion_tokens"],
            cost_gbp=float(cost) if cost is not None else None,
            latency_ms=ms,
        )
        metadata = {
            key: h.get(f"x-gearbox-{key}")
            for key in ("tier", "router", "reason", "cache", "fallback", "policy", "note")
            if h.get(f"x-gearbox-{key}") is not None
        }
        metadata["finish_reason"] = data["choices"][0].get("finish_reason")
        return AgentResult(final_answer=answer, steps=[step], metadata=metadata)
