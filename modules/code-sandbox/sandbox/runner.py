"""Run untrusted Python in a throw-away, locked-down Docker container.

Design goals
------------
* Defence in depth: no network, non-root user, read-only root FS, no
  capabilities, no privilege escalation, CPU / memory / PID caps.
* The *container* is killed on timeout, not just the local ``docker`` client
  (killing only the client leaves the workload running on the host).
* Output is capped, so a ``while True: print(...)`` loop cannot exhaust memory.
* All limits are configuration, not code (see ``RunLimits.from_env``).
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path


class SandboxError(Exception):
    """Infrastructure problem (Docker missing / failed to start), not a user bug."""


@dataclass(frozen=True)
class RunLimits:
    image: str = "python:3.11-slim"
    timeout_seconds: float = 2.0
    cpus: str = "1"
    memory: str = "128m"
    pids_limit: int = 64
    max_output_bytes: int = 64 * 1024

    @classmethod
    def from_env(cls) -> "RunLimits":
        d = cls()
        return cls(
            image=os.getenv("SANDBOX_IMAGE", d.image),
            timeout_seconds=float(os.getenv("SANDBOX_TIMEOUT_SECONDS", d.timeout_seconds)),
            cpus=os.getenv("SANDBOX_CPUS", d.cpus),
            memory=os.getenv("SANDBOX_MEMORY", d.memory),
            pids_limit=int(os.getenv("SANDBOX_PIDS_LIMIT", d.pids_limit)),
            max_output_bytes=int(os.getenv("SANDBOX_MAX_OUTPUT_BYTES", d.max_output_bytes)),
        )


@dataclass(frozen=True)
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    output_truncated: bool = False


def build_command(name: str, host_dir: str, limits: RunLimits) -> list[str]:
    return [
        "docker", "run", "--rm", "--name", name,
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", "65534:65534",
        "--cpus", limits.cpus,
        "--memory", limits.memory,
        "--memory-swap", limits.memory,   # no swap: memory limit is a hard limit
        "--pids-limit", str(limits.pids_limit),
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-v", f"{host_dir}:/sandbox:ro",
        "-w", "/sandbox",
        limits.image,
        "python", "main.py",
    ]


def _kill_container(name: str) -> None:
    subprocess.run(["docker", "kill", name], capture_output=True, timeout=10, check=False)


def _drain(stream, sink: bytearray, cap: int, overflow: threading.Event) -> None:
    """Read until EOF, keeping at most ``cap`` bytes; flag if more arrived."""
    while chunk := stream.read(4096):
        room = cap - len(sink)
        if room > 0:
            sink.extend(chunk[:room])
        if len(chunk) > room:
            overflow.set()


def run_python(code: str, limits: RunLimits | None = None) -> RunResult:
    limits = limits or RunLimits.from_env()
    name = f"sbx-{uuid.uuid4().hex[:12]}"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp).resolve()
        (tmp_path / "main.py").write_text(code, encoding="utf-8")
        tmp_path.chmod(0o755)                       # readable by the unprivileged user
        (tmp_path / "main.py").chmod(0o644)

        try:
            proc = subprocess.Popen(
                build_command(name, str(tmp_path), limits),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise SandboxError("docker_not_found") from exc

        out, err = bytearray(), bytearray()
        overflow = threading.Event()
        readers = [
            threading.Thread(target=_drain, args=(proc.stdout, out, limits.max_output_bytes, overflow), daemon=True),
            threading.Thread(target=_drain, args=(proc.stderr, err, limits.max_output_bytes, overflow), daemon=True),
        ]
        for t in readers:
            t.start()

        timed_out = False
        try:
            proc.wait(timeout=limits.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
        if timed_out or overflow.is_set():
            _kill_container(name)
            proc.wait()
        for t in readers:
            t.join(timeout=2)

        return RunResult(
            exit_code=proc.returncode,
            stdout=out.decode("utf-8", "replace"),
            stderr=err.decode("utf-8", "replace"),
            timed_out=timed_out,
            output_truncated=overflow.is_set(),
        )
