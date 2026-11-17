"""Extract step: read from the GitHub API with the workflow's token.

Uses urllib only. Every request retries transient failures (HTTP 5xx, 429, and
network errors) with exponential backoff; 4xx errors fail fast because retrying
will not fix a bad token or a missing repo.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

API = "https://api.github.com"

_CALENDAR_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


class ExtractError(RuntimeError):
    """Raised when the API cannot supply data the run needs."""


def _request(url: str, token: str, *, body: dict | None = None,
             accept: str = "application/vnd.github+json", attempts: int = 4) -> bytes:
    headers = {
        "Accept": accept,
        "Authorization": f"Bearer {token}",
        "User-Agent": "profile-pipeline",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    for attempt in range(attempts):
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as err:
            if err.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise ExtractError(f"{url}: HTTP {err.code}") from err
        except urllib.error.URLError as err:
            if attempt == attempts - 1:
                raise ExtractError(f"{url}: {err.reason}") from err
        time.sleep(2 ** attempt)
    raise ExtractError(f"{url}: exhausted retries")  # unreachable, keeps type checkers happy


def fetch_calendar(login: str, token: str) -> list[dict]:
    """Daily contribution counts for roughly the last year, oldest first.

    The workflow token is not the user's own, so private contributions are not
    included; the gauge's source line says "public contributions" for that reason.
    """
    raw = _request(f"{API}/graphql", token,
                   body={"query": _CALENDAR_QUERY, "variables": {"login": login}})
    payload = json.loads(raw)
    if payload.get("errors"):
        raise ExtractError(f"graphql: {payload['errors'][0].get('message')}")
    try:
        weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    except (KeyError, TypeError) as err:
        raise ExtractError("graphql: unexpected response shape") from err
    return [{"date": d["date"], "count": d["contributionCount"]}
            for w in weeks for d in w["contributionDays"]]


def fetch_public_repo_count(login: str, token: str) -> int:
    payload = json.loads(_request(f"{API}/users/{login}", token))
    return int(payload["public_repos"])


def fetch_readme_at_head(repo: str, token: str) -> tuple[str, str]:
    """Return (commit sha, README text) for the default branch head of ``repo``.

    The README is read at that exact sha so the card can cite a fixed commit.
    """
    meta = json.loads(_request(f"{API}/repos/{repo}", token))
    branch = meta["default_branch"]
    head = json.loads(_request(f"{API}/repos/{repo}/commits/{branch}", token))
    sha = head["sha"]
    text = _request(f"{API}/repos/{repo}/readme?ref={sha}", token,
                    accept="application/vnd.github.raw").decode("utf-8", errors="replace")
    return sha, text
