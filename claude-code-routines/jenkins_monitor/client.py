# claude-code-routines/jenkins_monitor/client.py
from __future__ import annotations

import datetime as dt
import os

import requests

from . import JENKINS_BASE_URL
from .models import BuildInfo

_ALL_JOBS_TREE = (
    "jobs[name,color,lastBuild[number,result,building,timestamp],"
    "lastSuccessfulBuild[number,timestamp],lastFailedBuild[number,timestamp]]"
)
_BUILDS_TREE = "builds[number,result,building,timestamp]"
_DETAIL_TREE = "number,result,duration,actions[parameters[name,value]]"


class AuthMissing(RuntimeError):
    """JENKINS_USER / JENKINS_API_TOKEN are not both present in the environment."""


class JenkinsUnreachable(RuntimeError):
    """Jenkins returned a non-2xx status or the request failed."""


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


_build = build_from_blob


class JenkinsClient:
    def __init__(self, base_url: str, user: str, token: str, session=None, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self._auth = (user, token)
        self._session = session or requests.Session()
        self._timeout = timeout

    def _get(self, path: str, params: dict | None = None):
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.get(url, params=params, auth=self._auth, timeout=self._timeout)
        except Exception as exc:  # noqa: BLE001 - network layer, re-raised as our type
            raise JenkinsUnreachable(f"GET {url} failed: {exc}") from exc
        if not getattr(resp, "ok", False):
            raise JenkinsUnreachable(f"GET {url} returned HTTP {resp.status_code}")
        return resp

    def all_jobs(self) -> dict[str, dict]:
        resp = self._get("/api/json", {"tree": _ALL_JOBS_TREE})
        return {j["name"]: j for j in resp.json().get("jobs", []) if j.get("name")}

    def recent_builds(self, job: str, limit: int = 25) -> list[BuildInfo]:
        """Newest-first builds, including NOT_BUILT seed runs (callers filter)."""
        resp = self._get(f"/job/{job}/api/json", {"tree": f"{_BUILDS_TREE}{{0,{limit}}}"})
        out = [_build(b) for b in resp.json().get("builds", [])]
        return [b for b in out if b is not None]

    def build_detail(self, job: str, number: int) -> tuple[str | None, dict[str, str]]:
        resp = self._get(f"/job/{job}/{number}/api/json", {"tree": _DETAIL_TREE})
        data = resp.json()
        params: dict[str, str] = {}
        for action in data.get("actions", []) or []:
            for p in action.get("parameters", []) or []:
                if p.get("name") is not None:
                    params[p["name"]] = p.get("value")
        return data.get("result"), params

    def console(self, job: str, number: int) -> str:
        return self._get(f"/job/{job}/{number}/consoleText").text


def from_env(base_url: str = JENKINS_BASE_URL, session=None) -> JenkinsClient:
    user = os.environ.get("JENKINS_USER") or ""
    token = os.environ.get("JENKINS_API_TOKEN") or ""
    missing = [n for n, v in (("JENKINS_USER", user), ("JENKINS_API_TOKEN", token)) if not v]
    if missing:
        raise AuthMissing(
            f"missing/empty environment variable(s): {', '.join(missing)}. "
            "Mint a token at http://jenkins.libremax.com/me/security/ and set it at User scope."
        )
    return JenkinsClient(base_url, user, token, session=session)
