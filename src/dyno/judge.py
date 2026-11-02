"""LLM judge: one structured call to Claude, priced in GBP, under a spending cap.

The reply must match a Pydantic model (structured outputs), so a judge can't answer in
a shape the scorer can't read. Prompts are versioned files in dyno/prompts/; every score
records the prompt version and hash, the model and the cost, so a judged number can
always be traced back to exactly what produced it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from dyno.config import get_settings

PROMPTS = Path(__file__).resolve().parent / "prompts"

# USD per million tokens, Anthropic first-party API (checked 2026-11-02). Haiku 5.5's
# rate rises above 100K input tokens; Dyno caps judge input well below that.
PRICES_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}
USD_TO_GBP = 0.79  # same rate as Scout's config, so costs compare like for like
MAX_TOKENS = 8000  # thinking counts towards it; verdicts themselves are short


class JudgeError(RuntimeError):
    pass


@dataclass(frozen=True)
class Prompt:
    name: str  # e.g. judge_task_v1
    text: str

    @property
    def version(self) -> str:
        return f"{self.name}:{hashlib.sha256(self.text.encode()).hexdigest()[:8]}"


@lru_cache
def load_prompt(name: str) -> Prompt:
    path = PROMPTS / f"{name}.md"
    if not path.exists():
        raise ValueError(f"no judge prompt {name!r} in {PROMPTS}")
    return Prompt(name, path.read_text(encoding="utf-8").strip())


@dataclass
class Verdict[T: BaseModel]:
    parsed: T
    model: str
    input_tokens: int
    output_tokens: int
    cost_gbp: float

    def meta(self, prompt: Prompt) -> dict[str, Any]:
        """What every judged score stores alongside the verdict."""
        return {
            "model": self.model,
            "prompt": prompt.version,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_gbp": self.cost_gbp,
        }


def cost_gbp(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in PRICES_USD_PER_MTOK:
        raise JudgeError(f"no price for {model}: add it to PRICES_USD_PER_MTOK")
    usd_in, usd_out = PRICES_USD_PER_MTOK[model]
    return (input_tokens * usd_in + output_tokens * usd_out) / 1e6 * USD_TO_GBP


class Judge:
    def __init__(
        self,
        model: str | None = None,
        *,
        effort: str | None = None,
        budget_gbp: float | None = None,
        client: Any = None,
    ) -> None:
        settings = get_settings()
        self.model = model or settings.judge_model
        self.effort = effort or settings.judge_effort
        self.budget_gbp = settings.judge_budget_gbp if budget_gbp is None else budget_gbp
        self.spent_gbp = 0.0
        self.calls = 0
        if client is None:
            import anthropic  # here, so commands that never judge don't need the SDK

            key = settings.anthropic_api_key
            if key is None:
                raise JudgeError("ANTHROPIC_API_KEY is not set (put it in .env)")
            client = anthropic.Anthropic(api_key=key.get_secret_value(), max_retries=4)
        self.client = client

    def ask[T: BaseModel](self, prompt: Prompt, user: str, output: type[T]) -> Verdict[T]:
        if self.spent_gbp >= self.budget_gbp:
            raise JudgeError(
                f"judge budget used up (GBP {self.spent_gbp:.4f} of {self.budget_gbp}); "
                "raise JUDGE_BUDGET_GBP to continue"
            )
        resp = self.client.messages.parse(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=prompt.text,
            messages=[{"role": "user", "content": user}],
            output_format=output,
            output_config={"effort": self.effort},
        )
        cost = cost_gbp(self.model, resp.usage.input_tokens, resp.usage.output_tokens)
        self.spent_gbp += cost
        self.calls += 1
        # Check stop_reason before reading the content: a refusal or a cut-off reply
        # isn't a verdict.
        if resp.stop_reason in ("refusal", "max_tokens"):
            raise JudgeError(f"judge stopped early: {resp.stop_reason}")
        parsed = resp.parsed_output
        if parsed is None:
            raise JudgeError(f"judge returned no valid {output.__name__}")
        return Verdict(parsed, self.model, resp.usage.input_tokens, resp.usage.output_tokens, cost)


_judge: Judge | None = None


def get_judge() -> Judge:
    """One judge per process, so the budget covers a whole dyno command."""
    global _judge
    if _judge is None:
        _judge = Judge()
    return _judge


def current_judge() -> Judge | None:
    """The shared judge if one was started (for reporting spend), without starting one."""
    return _judge


def set_judge(judge: Judge | None) -> None:
    """Swap the shared judge (tests use a fake client)."""
    global _judge
    _judge = judge
