"""Turn a raw ``RunResult`` into a grading verdict."""
from __future__ import annotations

from enum import Enum

from .runner import RunResult


class Verdict(str, Enum):
    PASSED = "passed"
    WRONG_ANSWER = "wrong_answer"
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT = "timeout"
    OUTPUT_LIMIT = "output_limit"


def _norm(text: str) -> str:
    return (text or "").replace("\r\n", "\n").strip()


def judge(result: RunResult, expected_output: str) -> Verdict:
    if result.timed_out:
        return Verdict.TIMEOUT
    if result.output_truncated:
        return Verdict.OUTPUT_LIMIT
    if result.exit_code != 0:
        if "SyntaxError" in result.stderr or "IndentationError" in result.stderr:
            return Verdict.SYNTAX_ERROR
        return Verdict.RUNTIME_ERROR
    return Verdict.PASSED if _norm(result.stdout) == _norm(expected_output) else Verdict.WRONG_ANSWER
