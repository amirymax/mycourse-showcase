import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.conf import settings

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if not settings.configured:
    settings.configure(SERVICE_API_KEY="test-key-123")

from hardening.permissions import HasServiceAPIKey
from hardening.secret_filter import contains_secret


def req(key=None):
    return SimpleNamespace(headers={"X-API-Key": key} if key is not None else {})


def test_api_key_ok_and_wrong():
    p = HasServiceAPIKey()
    assert p.has_permission(req("test-key-123"), None)
    assert not p.has_permission(req("nope"), None)
    assert not p.has_permission(req(), None)


def test_fail_closed_when_unconfigured():
    settings.SERVICE_API_KEY = ""
    try:
        assert not HasServiceAPIKey().has_permission(req(""), None)
    finally:
        settings.SERVICE_API_KEY = "test-key-123"


@pytest.mark.parametrize("text,expected", [
    ('api_key = "abcdefghijklmnopqrstuvwxyz"', True),
    ("123456789:" + "A" * 35, True),
    ("sk-" + "a" * 40, True),
    ("print('hello')", False),
    ("api_key = None", False),
])
def test_secret_filter(text, expected):
    assert contains_secret(text) is expected
