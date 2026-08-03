# claude-code-routines/jenkins_monitor/client.py
from __future__ import annotations

import datetime as dt
import os
import time

import requests

from . import JENKINS_BASE_URL
from .models import BuildInfo

_ALL_JOBS_TREE = (
    "jobs[name,color,lastBuild[number,result,building,timestamp],"
    "lastSuccessfulBuild[number,timestamp],lastFailedBuild[number,timestamp]]"
)
_BUILDS_TREE = "builds[number,result,building,timestamp]"
_DETAIL_TREE = "number,result,duration,actions[parameters[name,value]]"

#: Transport failures and 5xx responses are retried: a controller restart, a proxy
#: hiccup or a reset connection is transient, and reporting a job as unreadable because
#: one request happened to arrive during a restart is a false negative. 4xx is NOT
#: retried - 401/403/404 are deterministic answers about auth or the job's existence, so
#: retrying only delays the report without changing the outcome.
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 0.5


class AuthMissing(RuntimeError):
    """JENKINS_USER / JENKINS_API_TOKEN are not both present in the environment."""


class JenkinsUnreachable(RuntimeError):
    """Jenkins returned a non-2xx status, an undecodable body, or the request failed."""


def ms_to_dt(ms: int | None) -> dt.datetime | None:
    """Jenkins epoch milliseconds (UTC) to a tz-aware datetime. 0/None -> None."""
    if not ms:
        return None
    return dt.datetime.fromtimestamp(ms / 1000, dt.UTC)


def build_from_blob(blob: dict | None) -> BuildInfo | None:
    if not blob:
        return None
    return BuildInfo(
        number=blob.get("number", 0),
        result=blob.get("result"),
        timestamp=ms_to_dt(blob.get("timestamp")),
        building=bool(blob.get("building", False)),
    )


class JenkinsClient:
    def __init__(
        self,
        base_url: str,
        user: str,
        token: str,
        session=None,
        timeout: float = 60.0,
        sleep=None,
        max_attempts: int = MAX_ATTEMPTS,
        backoff_seconds: float = BACKOFF_SECONDS,
    ):
        self.base_url = base_url.rstrip("/")
        self._auth = (user, token)
        self._session = session or requests.Session()
        self._timeout = timeout
        # Injectable so tests exercise the retry path without spending real wall time.
        self._sleep = sleep if sleep is not None else time.sleep
        self._max_attempts = max(1, int(max_attempts))
        self._backoff = float(backoff_seconds)

    def _get(self, path: str, params: dict | None = None):
        """GET with bounded retry; raises JenkinsUnreachable once retries are exhausted."""
        url = f"{self.base_url}{path}"
        attempt = 0
        while True:
            attempt += 1
            cause: BaseException | None = None
            try:
                resp = self._session.get(url, params=params, auth=self._auth, timeout=self._timeout)
            except requests.exceptions.RequestException as exc:
                # Deliberately NOT `except Exception`. A TypeError/AttributeError raised by
                # our own code inside this call would otherwise be reported as
                # JenkinsUnreachable, which callers degrade into "could not read" - a
                # programming bug masquerading as a transient infra blip, and (before the
                # classifier fix) a route to a false GREEN.
                cause = exc
                detail = f"GET {url} failed: {exc}"
                retryable = True
            else:
                if getattr(resp, "ok", False):
                    return resp
                status = getattr(resp, "status_code", 0)
                detail = f"GET {url} returned HTTP {status}"
                retryable = status >= 500
            if not retryable or attempt >= self._max_attempts:
                raise JenkinsUnreachable(f"{detail} (after {attempt} attempt(s))") from cause
            self._sleep(self._backoff * (2 ** (attempt - 1)))

    def _json(self, path: str, params: dict | None = None) -> dict:
        """GET and decode JSON inside the client's own error boundary.

        `resp.json()` used to be called by each caller, i.e. outside `_get`'s wrapper. A
        proxy or an expired session answering HTTP 200 with an HTML login page raises
        requests.exceptions.JSONDecodeError, which `cli.py` does not catch - so the whole
        unattended run died with a traceback, producing no report and no snapshot. A body
        we cannot decode is the same class of event as a transport failure, so it is
        reported as such and stays inside the per-job isolation the CLI already has.
        """
        resp = self._get(path, params)
        url = f"{self.base_url}{path}"
        try:
            data = resp.json()
        except (ValueError, requests.exceptions.RequestException) as exc:
            raise JenkinsUnreachable(
                f"GET {url} returned a body that is not JSON "
                f"(an HTTP 200 login page or proxy interstitial looks exactly like this): {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise JenkinsUnreachable(f"GET {url} returned JSON {type(data).__name__}, expected an object")
        return data

    def all_jobs(self) -> dict[str, dict]:
        data = self._json("/api/json", {"tree": _ALL_JOBS_TREE})
        return {j["name"]: j for j in data.get("jobs", []) if j.get("name")}

    def recent_builds(self, job: str, limit: int = 25) -> list[BuildInfo]:
        """Newest-first builds, including NOT_BUILT seed runs (callers filter)."""
        data = self._json(f"/job/{job}/api/json", {"tree": f"{_BUILDS_TREE}{{0,{limit}}}"})
        out = [build_from_blob(b) for b in data.get("builds", [])]
        return [b for b in out if b is not None]

    def build_detail(self, job: str, number: int) -> tuple[str | None, dict[str, str]]:
        data = self._json(f"/job/{job}/{number}/api/json", {"tree": _DETAIL_TREE})
        params: dict[str, str] = {}
        for action in data.get("actions", []) or []:
            for p in action.get("parameters", []) or []:
                if p.get("name") is not None:
                    params[p["name"]] = p.get("value")
        return data.get("result"), params

    def console(self, job: str, number: int) -> str:
        return self._get(f"/job/{job}/{number}/consoleText").text


def _read_user_scope_var(name: str) -> str:
    """Read a Windows User-scope environment variable straight from the registry.

    A process started BEFORE a User-scope variable was set never sees it, and neither
    does anything it spawns - the environment is copied at process creation. The daily
    run is launched by a long-lived scheduler, so relying on os.environ alone meant a
    token set today was invisible until that scheduler restarted, turning every run
    into a reported access gap. Reading HKCU\\Environment sidesteps that entirely.

    Returns "" on any failure (non-Windows, missing key, permission error) so the
    caller falls through to its normal missing-credential error.
    """
    try:
        import winreg
    except ImportError:
        return ""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
        return str(value) if value else ""
    except OSError:
        return ""


def resolve_credential(name: str) -> str:
    """Current process environment first, Windows User scope second."""
    return (os.environ.get(name) or "") or _read_user_scope_var(name)


def from_env(base_url: str = JENKINS_BASE_URL, session=None) -> JenkinsClient:
    user = resolve_credential("JENKINS_USER")
    token = resolve_credential("JENKINS_API_TOKEN")
    missing = [n for n, v in (("JENKINS_USER", user), ("JENKINS_API_TOKEN", token)) if not v]
    if missing:
        raise AuthMissing(
            f"missing/empty environment variable(s): {', '.join(missing)}. "
            "Mint a token at http://jenkins.libremax.com/me/security/ and set it at User scope."
        )
    return JenkinsClient(base_url, user, token, session=session)
