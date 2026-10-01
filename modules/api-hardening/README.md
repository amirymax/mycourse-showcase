# api-hardening — small, reusable DRF protections

Three independent pieces that came out of running a public-facing API for real users.

| File | Purpose |
|---|---|
| `permissions.py` | `X-API-Key` permission for server-to-server calls: constant-time compare, **fail closed** when unconfigured. |
| `throttling.py` + `models.py` | DRF throttles that additionally record every block in the DB, so an operator can see/clear who is blocked (DRF's own state lives in an opaque cache). One throttle scope per abuse surface (login, password reset, paid third-party calls). |
| `secret_filter.py` | Rejects text that looks like a credential *before* it is forwarded to an external LLM grader. |

## Key decisions

- **Fail closed.** A missing `SERVICE_API_KEY` must disable the endpoint, never open it.
- **Observability without changing semantics.** The throttle mixin wraps `throttle_failure`;
  limits behave exactly like stock DRF, and a DB error while logging is swallowed.
- **Separate buckets for expensive endpoints.** Calls that cost money get their own, stricter
  rate than generic anonymous traffic.
- **Heuristic secret filter.** Prefers false positives to leaking a key to a third party.

## Settings sketch

```python
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {"login": "20/min", "password_reset": "5/hour", "expensive_call": "10/hour"},
}
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "")
```

## Tests

```bash
pip install -r requirements.txt && pytest
```
