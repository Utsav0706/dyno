"""A free, deterministic agent for tests and for trying Dyno without an API key.

It acts like a tiny tool-using agent: "plan" (an llm_call), maybe call one tool
(`calculator` or `lookup`), then "answer" (another llm_call). Token counts are word
counts and cost is zero. The same input always gives the same steps, so tests can
assert exact trajectories.

Inputs containing "crash" raise an error on purpose, to exercise the runner's
error handling.
"""

from __future__ import annotations

import ast
import operator
import re

from dyno.agent import AgentResult, Step

MODEL = "example-model"

FACTS = {
    "capital of france": "Paris",
    "capital of japan": "Tokyo",
    "boiling point of water": "100 degrees Celsius at sea level",
    "speed of light": "299,792,458 metres per second",
}

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}
_EXPR = re.compile(r"[-+*/().\d\s]*\d[-+*/().\d\s]*[-+*/][-+*/().\d\s]*\d[-+*/().\d\s]*")


def calculate(expr: str) -> float:
    """Evaluate + - * / arithmetic safely (no eval)."""

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError(f"unsupported expression: {expr!r}")

    return ev(ast.parse(expr.strip(), mode="eval").body)


def _llm(name: str, prompt: str, reply: str) -> Step:
    return Step(
        type="llm_call",
        name=MODEL,
        args={"purpose": name},
        output=reply,
        input_tokens=len(prompt.split()),
        output_tokens=len(reply.split()),
        cost_gbp=0.0,
        latency_ms=0.0,
    )


class ExampleAgent:
    def run(self, input: str) -> AgentResult:
        text = input.lower()
        if "crash" in text:
            raise RuntimeError("example agent crashed on purpose")

        steps: list[Step] = []
        match = _EXPR.search(input)
        fact_key = next((key for key in FACTS if key in text), None)

        if match:
            expr = match.group().strip()
            steps.append(_llm("plan", input, f"use calculator on {expr}"))
            steps.append(Step(type="tool_call", name="calculator", args={"expression": expr}))
            value = calculate(expr)
            result = f"{value:g}"
            steps.append(Step(type="tool_result", name="calculator", output=result))
            answer = f"The answer is {result}."
        elif fact_key:
            steps.append(_llm("plan", input, f"use lookup on {fact_key}"))
            steps.append(Step(type="tool_call", name="lookup", args={"query": fact_key}))
            steps.append(Step(type="tool_result", name="lookup", output=FACTS[fact_key]))
            answer = f"{FACTS[fact_key]}."
        else:
            answer = "I don't know."

        steps.append(_llm("answer", input, answer))
        return AgentResult(final_answer=answer, steps=steps)
