"""Fetch public repos and recent commits from the GitHub REST API."""

import os
from datetime import datetime, timezone

import requests

from generator import UserError

API = "https://api.github.com"


def _get(url: str, params: dict | None = None):
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
    except requests.RequestException:
        raise UserError("Couldn't reach GitHub. Check your internet connection and try again.")

    if r.status_code in (403, 429) and r.headers.get("X-RateLimit-Remaining") == "0":
        reset = r.headers.get("X-RateLimit-Reset")
        when = datetime.fromtimestamp(int(reset)).strftime("%I:%M %p") if reset else "in about an hour"
        raise UserError(
            f"GitHub's rate limit was hit. Try again after {when}, "
            "or set a GITHUB_TOKEN environment variable for a higher limit."
        )
    if r.status_code == 404:
        return None
    if r.status_code == 409:  # empty repository
        return []
    if not r.ok:
        raise UserError(f"GitHub returned an error ({r.status_code}). Try again in a few minutes.")
    return r.json()


def list_repos(username: str) -> list[dict]:
    repos = _get(f"{API}/users/{username}/repos", {"type": "owner", "per_page": 100})
    if repos is None:
        raise UserError(f'GitHub user "{username}" wasn\'t found. Check "github_username" in config.json.')
    return [r for r in repos if not r.get("fork") and not r.get("archived")]


TRAILERS = ("co-authored-by:", "signed-off-by:", "claude-session:")


def _strip_trailers(message: str) -> str:
    """Drop git trailer lines (Co-Authored-By etc.) that add noise to prompts."""
    lines = [l for l in message.strip().splitlines() if not l.strip().lower().startswith(TRAILERS)]
    return "\n".join(lines).strip()


def list_branches(username: str, repo: str) -> list[str]:
    branches = _get(f"{API}/repos/{username}/{repo}/branches", {"per_page": 100}) or []
    return [b["name"] for b in branches]


def commits_since(username: str, repo: str, since: datetime) -> list[dict]:
    """Commits since `since` on every branch (so unmerged PR branches count), newest first.

    No author filter: these are the user's own repos, and commits made by Claude Code
    or other tools on their behalf may not be authored under their GitHub account.
    """
    since_iso = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen, commits = set(), []
    for branch in list_branches(username, repo) or [None]:
        params = {"since": since_iso, "per_page": 100}
        if branch:
            params["sha"] = branch
        for c in _get(f"{API}/repos/{username}/{repo}/commits", params) or []:
            if c["sha"] in seen:
                continue
            seen.add(c["sha"])
            message = _strip_trailers(c["commit"]["message"])
            if message.startswith("Merge"):
                continue
            commits.append({
                "repo": repo,
                "branch": branch or "",
                "date": c["commit"]["author"]["date"],
                "message": message,
                "url": c.get("html_url", ""),
            })
    commits.sort(key=lambda c: c["date"], reverse=True)
    return commits


def _pushed_since(repo: dict, since: datetime) -> bool:
    pushed = repo.get("pushed_at")
    if not pushed:
        return True
    return datetime.fromisoformat(pushed.replace("Z", "+00:00")) >= since


def recent_activity(username: str, since: datetime) -> dict[str, list[dict]]:
    """Commits since `since`, grouped by repo. Repos with no commits are left out."""
    activity = {}
    for repo in list_repos(username):
        if not _pushed_since(repo, since):  # saves API calls on quiet repos
            continue
        commits = commits_since(username, repo["name"], since)
        if commits:
            activity[repo["name"]] = commits
    return activity


def summary_line(activity: dict[str, list[dict]]) -> str:
    if not activity:
        return "No new commits since your last post."
    return " | ".join(f"{repo}: {len(c)} commit{'s' if len(c) != 1 else ''}" for repo, c in activity.items())
