import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sandbox import RunLimits, RunResult, Verdict, judge
from sandbox.runner import build_command


def test_command_is_locked_down():
    cmd = build_command("sbx-test", "/host/tmp", RunLimits())
    joined = " ".join(cmd)
    for flag in ("--network none", "--read-only", "--cap-drop ALL",
                 "--security-opt no-new-privileges", "--user 65534:65534"):
        assert flag in joined
    assert "/host/tmp:/sandbox:ro" in cmd


@pytest.mark.parametrize("result,expected,verdict", [
    (RunResult(0, "42\r\n", ""), "42", Verdict.PASSED),
    (RunResult(0, "41", ""), "42", Verdict.WRONG_ANSWER),
    (RunResult(1, "", "IndentationError: x"), "", Verdict.SYNTAX_ERROR),
    (RunResult(1, "", "ZeroDivisionError"), "", Verdict.RUNTIME_ERROR),
    (RunResult(-9, "", "", timed_out=True), "", Verdict.TIMEOUT),
    (RunResult(0, "x" * 10, "", output_truncated=True), "", Verdict.OUTPUT_LIMIT),
])
def test_judge(result, expected, verdict):
    assert judge(result, expected) == verdict


def _docker_ok():
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=10).returncode == 0
    except Exception:
        return False


@pytest.mark.skipif(not _docker_ok(), reason="docker not available")
def test_integration_hello_and_infinite_loop():
    from sandbox import run_python
    ok = run_python("print('hi')", RunLimits(timeout_seconds=20))
    assert ok.stdout.strip() == "hi"
    loop = run_python("while True: pass", RunLimits(timeout_seconds=2))
    assert loop.timed_out
