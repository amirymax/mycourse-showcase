# code-sandbox — running untrusted student code

Homework in the course is "write Python, get automatic feedback". That means executing
arbitrary code from the internet, so the runner is built around the assumption that the
code is hostile.

## How it works

```
submission ──► run_python() ──► docker run (locked down) ──► RunResult ──► judge() ──► Verdict
```

1. The code is written to a fresh temp dir, mounted **read-only** into a one-shot container.
2. The container runs with no network, a read-only root FS (+ small `noexec` tmpfs),
   all capabilities dropped, `no-new-privileges`, a non-root UID, and CPU / memory
   (no swap) / PID caps.
3. stdout/stderr are drained by reader threads with a **byte cap**.
4. On timeout *or* output overflow the **container is killed by name** (`docker kill`).
5. `judge()` maps the result to a verdict: passed / wrong answer / syntax error /
   runtime error / timeout / output limit.

## Key decisions

- **Kill the container, not the client.** The first version used `subprocess.run(timeout=…)`,
  which only kills the local `docker` CLI — the workload kept running on the host.
  Named containers + `docker kill` fix that.
- **Cap output.** An infinite `print` loop would otherwise fill memory in the web process.
- **Limits are configuration** (`SANDBOX_*` env vars, see `.env.example`), and the defaults
  here are illustrative.
- **Infra errors are separate from user errors** (`SandboxError` vs. verdicts), so a missing
  Docker daemon never shows up to a student as "wrong answer".

## Known limits (honest notes)

Docker isolation is a shared-kernel boundary. For stronger guarantees run it on a dedicated
host/VM, or swap the runtime for gVisor/Firecracker (`--runtime runsc`) — the module keeps
the container command in one function (`build_command`) for that reason. Fork-bomb and
CPU limits are per-container; add a global concurrency limit (queue) in front of it.

## Tests

```bash
pip install -r requirements.txt
pytest          # unit tests always run; the Docker integration test runs if Docker is available
```
