# tests/test_jenkins_client.py
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pytest
import requests

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


class _RaisingSession:
    """Session double whose get() raises before any HTTP response exists.

    Models transport-level failures (DNS errors, connection resets, timeouts) that never
    reach the ok/status_code branch in `_get` - the caller never touches the network either.
    """

    def __init__(self, exc):
        self._exc = exc

    def get(self, url, params=None, auth=None, timeout=None):
        raise self._exc


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


def test_get_raises_jenkins_unreachable_on_transport_exception():
    """The transport-exception branch of `_get` (session.get() itself raising) must be
    normalized to JenkinsUnreachable, with the original exception preserved as __cause__.

    The exception is a requests.exceptions.RequestException on purpose: `_get` narrows its
    except clause to that base class so a programming error cannot be laundered into an
    infrastructure verdict (see test_get_does_not_swallow_programming_errors)."""
    original = requests.exceptions.ConnectionError("boom")
    sess = _RaisingSession(original)
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess, sleep=lambda _s: None)
    with pytest.raises(client.JenkinsUnreachable) as exc_info:
        c.all_jobs()
    assert exc_info.value.__cause__ is original


def test_non_2xx_exception_message_never_leaks_token():
    """Regression guard: if a future edit ever logs `self._auth` or embeds credentials in a
    URL when building the non-2xx JenkinsUnreachable message, this must fail loudly - a
    leaked token in an exception string can end up in logs, crash reports, or CI output."""
    token = "tok-SENTINEL-do-not-leak"
    sess = _Session({"/api/json": _Resp(403, text="forbidden")})
    c = client.JenkinsClient("http://jenkins.example", "hzeng", token, session=sess)
    with pytest.raises(client.JenkinsUnreachable) as exc_info:
        c.all_jobs()
    assert token not in str(exc_info.value), (
        "Auth token leaked into str(JenkinsUnreachable) on the non-2xx path - "
        "this would expose credentials in any log/report that captures exception text."
    )
    assert token not in repr(exc_info.value), (
        "Auth token leaked into repr(JenkinsUnreachable) on the non-2xx path - "
        "this would expose credentials in any log/report that captures exception text."
    )


def test_transport_exception_message_never_leaks_token():
    """Regression guard: same as above, but for the transport-exception path - a future edit
    that folds `self._auth` into the wrapped message would leak the token via this branch too."""
    token = "tok-SENTINEL-do-not-leak"
    original = requests.exceptions.ConnectionError("connection reset by peer")
    sess = _RaisingSession(original)
    c = client.JenkinsClient("http://jenkins.example", "hzeng", token, session=sess, sleep=lambda _s: None)
    with pytest.raises(client.JenkinsUnreachable) as exc_info:
        c.all_jobs()
    assert token not in str(exc_info.value), (
        "Auth token leaked into str(JenkinsUnreachable) on the transport-exception path - "
        "this would expose credentials in any log/report that captures exception text."
    )
    assert token not in repr(exc_info.value), (
        "Auth token leaked into repr(JenkinsUnreachable) on the transport-exception path - "
        "this would expose credentials in any log/report that captures exception text."
    )


def test_from_env_raises_when_token_missing(monkeypatch):
    monkeypatch.delenv("JENKINS_API_TOKEN", raising=False)
    monkeypatch.setenv("JENKINS_USER", "hzeng")
    monkeypatch.setattr(client, "_read_user_scope_var", lambda name: "")
    with pytest.raises(client.AuthMissing, match="JENKINS_API_TOKEN"):
        client.from_env()


def test_from_env_raises_when_token_is_empty(monkeypatch):
    monkeypatch.setenv("JENKINS_USER", "hzeng")
    monkeypatch.setenv("JENKINS_API_TOKEN", "")
    monkeypatch.setattr(client, "_read_user_scope_var", lambda name: "")
    with pytest.raises(client.AuthMissing):
        client.from_env()


# --- Final review, CRITICAL 1 part 3: `_get` used to catch bare `Exception`, so a
# --- TypeError in our own client code was reported as JenkinsUnreachable, which the CLI
# --- degraded into an empty build list and (before the classifier fix) a false GREEN.
# --- Transport blips and 5xx are now retried; 4xx is a deterministic answer and is not.


class _SequenceSession:
    """Returns/raises a scripted item per call so retry behaviour is observable."""

    def __init__(self, items):
        self._items = list(items)
        self.calls = 0

    def get(self, url, params=None, auth=None, timeout=None):
        self.calls += 1
        item = self._items[min(self.calls - 1, len(self._items) - 1)]
        if isinstance(item, BaseException):
            raise item
        return item


def _no_sleep():
    slept = []
    return slept, slept.append


def test_get_does_not_swallow_programming_errors_as_unreachable():
    """A TypeError from client code must propagate, NOT become JenkinsUnreachable.

    JenkinsUnreachable is a claim about infrastructure. Laundering a bug into it means the
    CLI reports 'could not read build history' for a defect in this package - and, before
    the classifier fix, produced a GREEN for a red job.
    """
    sess = _RaisingSession(TypeError("recent_builds() got an unexpected keyword argument"))
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess, sleep=lambda _s: None)
    with pytest.raises(TypeError):
        c.all_jobs()


def test_get_retries_transport_failure_then_succeeds():
    payload = {"jobs": [{"name": "quant-x"}]}
    sess = _SequenceSession(
        [
            requests.exceptions.ConnectionError("reset"),
            requests.exceptions.ConnectionError("reset"),
            _Resp(200, payload),
        ]
    )
    slept, sleeper = _no_sleep()
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess, sleep=sleeper)
    assert "quant-x" in c.all_jobs()
    assert sess.calls == 3
    assert slept == [0.5, 1.0], "backoff must grow, and must be the injected sleep so tests never wait"


def test_get_retries_five_hundred_then_gives_up_after_three_attempts():
    sess = _SequenceSession([_Resp(500, text="oops")])
    slept, sleeper = _no_sleep()
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess, sleep=sleeper)
    with pytest.raises(client.JenkinsUnreachable, match="HTTP 500"):
        c.all_jobs()
    assert sess.calls == 3, "a 5xx is transient (controller restart) and must be retried"
    assert len(slept) == 2


def test_get_does_not_retry_four_hundred_level_status():
    sess = _SequenceSession([_Resp(403, text="forbidden")])
    slept, sleeper = _no_sleep()
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess, sleep=sleeper)
    with pytest.raises(client.JenkinsUnreachable, match="HTTP 403"):
        c.all_jobs()
    assert sess.calls == 1, "401/403/404 are deterministic answers - retrying only delays the report"
    assert slept == []


# --- Final review, IMPORTANT 1: `resp.json()` was called by each caller, outside `_get`'s
# --- error wrapper. A proxy or expired session answering HTTP 200 with an HTML login page
# --- raised requests.exceptions.JSONDecodeError, which cli.py does not catch - traceback,
# --- non-zero exit, no report and no snapshot for the whole fleet.


class _BadJsonResp:
    def __init__(self, text):
        self.status_code = 200
        self.ok = True
        self.text = text

    def json(self):
        raise requests.exceptions.JSONDecodeError("Expecting value", self.text, 0)


def test_html_login_page_with_http_200_raises_jenkins_unreachable_not_json_error():
    sess = _Session({"/api/json": _BadJsonResp("<html><body>Please log in</body></html>")})
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess, sleep=lambda _s: None)
    with pytest.raises(client.JenkinsUnreachable, match="not JSON"):
        c.all_jobs()


def test_recent_builds_and_build_detail_also_wrap_json_decode_failures():
    body = "<html>login</html>"
    sess = _Session({"/job/j": _BadJsonResp(body)})
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess, sleep=lambda _s: None)
    with pytest.raises(client.JenkinsUnreachable):
        c.recent_builds("j")
    with pytest.raises(client.JenkinsUnreachable):
        c.build_detail("j", 75)


def test_non_object_json_body_raises_jenkins_unreachable():
    """A JSON array decodes fine but has no .get - an AttributeError here would escape
    cli.py's JenkinsUnreachable handling exactly like the decode error did."""
    sess = _Session({"/api/json": _Resp(200, [1, 2, 3])})
    c = client.JenkinsClient("http://jenkins.example", "u", "t", session=sess, sleep=lambda _s: None)
    with pytest.raises(client.JenkinsUnreachable, match="expected an object"):
        c.all_jobs()
