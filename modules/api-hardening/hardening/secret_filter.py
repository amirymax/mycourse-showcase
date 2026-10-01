"""Refuse to forward text that looks like it contains credentials.

Learners paste code into an editor and some of it is sent to a third-party LLM
for grading. If a submission contains something that looks like a key or token,
it is rejected *before* leaving the server. Heuristic by design: favours false
positives (ask the learner to remove the string) over leaking a secret.
"""
import re

_SECRET_PATTERNS = [
    # chat-bot style tokens: 123456789:AAAA...
    re.compile(r"\d{8,10}:[A-Za-z0-9_-]{35}"),
    # explicit assignments: api_key = "...", secret_key: '...'
    re.compile(r"(?i)(bot[_-]?token|api[_-]?key|secret[_-]?key|access[_-]?token)\s*[=:]\s*[\"'][^\"']{15,}[\"']"),
    # well-known vendor key shapes
    re.compile(r"(?i)(sk-[A-Za-z0-9]{32,}|AIza[A-Za-z0-9_-]{32,})"),
]


def contains_secret(text: str) -> bool:
    return any(p.search(text) for p in _SECRET_PATTERNS)
