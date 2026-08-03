"""The daily run must find a User-scope credential even in a stale parent environment.

A process started BEFORE a Windows User-scope variable was set never sees it, and
neither does anything it spawns. The scheduler that launches the daily run is
long-lived, so os.environ alone meant a token set today stayed invisible until that
scheduler restarted - every run in between reporting an access gap instead of job
status. These tests pin the registry fallback that closes that hole.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROUTINES = Path(__file__).resolve().parents[1] / "claude-code-routines"
if str(_ROUTINES) not in sys.path:
    sys.path.insert(0, str(_ROUTINES))

from jenkins_monitor import client  # noqa: E402

SENTINEL = "tok-SENTINEL-do-not-leak"


def test_process_environment_wins_when_present(monkeypatch):
    monkeypatch.setenv("JENKINS_USER", "from-process")
    monkeypatch.setattr(client, "_read_user_scope_var", lambda name: "from-registry")
    assert client.resolve_credential("JENKINS_USER") == "from-process"


def test_falls_back_to_user_scope_when_process_env_missing(monkeypatch):
    monkeypatch.delenv("JENKINS_USER", raising=False)
    monkeypatch.setattr(client, "_read_user_scope_var", lambda name: "from-registry")
    assert client.resolve_credential("JENKINS_USER") == "from-registry"


def test_falls_back_when_process_env_is_empty_string(monkeypatch):
    """An empty value is as useless as an absent one and must not shadow the fallback."""
    monkeypatch.setenv("JENKINS_API_TOKEN", "")
    monkeypatch.setattr(client, "_read_user_scope_var", lambda name: SENTINEL)
    assert client.resolve_credential("JENKINS_API_TOKEN") == SENTINEL


def test_from_env_succeeds_on_user_scope_alone(monkeypatch):
    """The exact scenario that broke: nothing in os.environ, both values in User scope."""
    monkeypatch.delenv("JENKINS_USER", raising=False)
    monkeypatch.delenv("JENKINS_API_TOKEN", raising=False)
    monkeypatch.setattr(
        client,
        "_read_user_scope_var",
        lambda name: {"JENKINS_USER": "hzeng", "JENKINS_API_TOKEN": SENTINEL}.get(name, ""),
    )
    api = client.from_env(session=object())
    assert api._auth == ("hzeng", SENTINEL)


def test_auth_missing_still_raised_when_neither_source_has_it(monkeypatch):
    monkeypatch.delenv("JENKINS_USER", raising=False)
    monkeypatch.delenv("JENKINS_API_TOKEN", raising=False)
    monkeypatch.setattr(client, "_read_user_scope_var", lambda name: "")
    with pytest.raises(client.AuthMissing, match="JENKINS_USER"):
        client.from_env()


def test_read_user_scope_var_returns_empty_for_a_missing_name():
    """Real registry read, no mocks: an absent name degrades to "" and never raises,
    so the caller still gets a clean AuthMissing rather than an OSError traceback."""
    assert client._read_user_scope_var("JENKINS_DEFINITELY_NOT_SET_XYZ") == ""


def test_real_user_scope_read_finds_the_configured_user():
    """End-to-end against the actual registry: this is the hole that was fixed.

    Skips rather than fails if the machine has no User-scope JENKINS_USER, so the
    suite stays portable.
    """
    got = client._read_user_scope_var("JENKINS_USER")
    if not got:
        pytest.skip("no User-scope JENKINS_USER on this machine")
    assert got.strip() != ""
