# tests/test_jenkins_client.py
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pytest

_ROUTINES = Path(__file__).resolve().parents[1] / "claude-code-routines"
if str(_ROUTINES) not in sys.path:
    sys.path.insert(0, str(_ROUTINES))

from jenkins_monitor import client  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "jenkins"


class _Resp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code = status
        self._payload = payload
        self.text = text
        self.ok = 200 <= status < 300

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


class _Session:
    """Records calls; never needs a real network."""

    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    def get(self, url, params=None, auth=None, timeout=None):
        self.calls.append({"url": url, "params": params, "auth": auth})
        for pattern, resp in self._responses.items():
            if pattern in url:
                return resp
        return _Resp(404, text="not found")


def test_ms_to_dt_returns_utc_aware():
    got = client.ms_to_dt(1785000000000)
    assert got.tzinfo == dt.UTC
    assert client.ms_to_dt(None) is None
    assert client.ms_to_dt(0) is None


def test_all_jobs_keys_by_name():
    payload = json.loads((FIXTURES / "all_jobs.json").read_text(encoding="utf-8"))
    sess = _Session({"/api/json": _Resp(200, payload)})
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess)
    jobs = c.all_jobs()
    assert "quant-DailySimDataUpdateLP" in jobs
    assert jobs["quant-DailySimDataUpdateLP"]["lastBuild"]["number"] == 93


def test_all_jobs_sends_basic_auth_and_never_puts_token_in_url():
    payload = {"jobs": []}
    sess = _Session({"/api/json": _Resp(200, payload)})
    c = client.JenkinsClient("http://jenkins.example", "hzeng", "SECRET", session=sess)
    c.all_jobs()
    call = sess.calls[0]
    assert call["auth"] == ("hzeng", "SECRET")
    assert "SECRET" not in call["url"]
    assert "SECRET" not in json.dumps(call["params"])


def test_recent_builds_newest_first_and_parses_not_built():
    payload = {
        "builds": [
            {"number": 45, "result": "NOT_BUILT", "timestamp": 1785000000000},
            {"number": 44, "result": "SUCCESS", "timestamp": 1784000000000},
        ]
    }
    sess = _Session({"/job/j/api/json": _Resp(200, payload)})
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess)
    builds = c.recent_builds("j")
    assert [b.number for b in builds] == [45, 44]
    assert builds[0].did_work is False
    assert builds[1].did_work is True


def test_build_detail_extracts_parameters():
    payload = {
        "number": 75,
        "result": "FAILURE",
        "actions": [
            {"parameters": [{"name": "deal_type", "value": "JUMBO2_0_PSEUDO"}]},
            {},
        ],
    }
    sess = _Session({"/job/j/75/api/json": _Resp(200, payload)})
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess)
    result, params = c.build_detail("j", 75)
    assert result == "FAILURE"
    assert params["deal_type"] == "JUMBO2_0_PSEUDO"


def test_console_returns_text():
    sess = _Session({"/consoleText": _Resp(200, text="KeyError: 'Transition'")})
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess)
    assert "Transition" in c.console("j", 75)


def test_unreachable_raises_jenkins_unreachable():
    sess = _Session({"/api/json": _Resp(403, text="forbidden")})
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess)
    with pytest.raises(client.JenkinsUnreachable):
        c.all_jobs()


def test_from_env_raises_when_token_missing(monkeypatch):
    monkeypatch.delenv("JENKINS_API_TOKEN", raising=False)
    monkeypatch.setenv("JENKINS_USER", "hzeng")
    with pytest.raises(client.AuthMissing, match="JENKINS_API_TOKEN"):
        client.from_env()


def test_from_env_raises_when_token_is_empty(monkeypatch):
    monkeypatch.setenv("JENKINS_USER", "hzeng")
    monkeypatch.setenv("JENKINS_API_TOKEN", "")
    with pytest.raises(client.AuthMissing):
        client.from_env()
