import json
import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from generator import UserError, ai, github, history
from generator.config import load_config


# ---------- Config ----------

def test_config_created_on_first_run(tmp_path):
    path = tmp_path / "config.json"
    config = load_config(path, ask=lambda _: "someone")
    assert config["github_username"] == "someone"
    assert json.loads(path.read_text())["num_angles"] == 3


def test_config_bad_json(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{oops")
    with pytest.raises(UserError):
        load_config(path)


# ---------- Feature 1: history ----------

def test_first_run_uses_lookback():
    since = history.since_date({"posts": []}, 7)
    assert abs((history.now() - since) - timedelta(days=7)) < timedelta(seconds=5)


def test_posted_and_unposted(tmp_path):
    path = tmp_path / "data" / "history.json"
    data = history.load(path)
    assert data == {"posts": []}

    history.add_post(data, posted=True, angle=None, repos=[], ai_draft="a",
                     final_text="b", visual_suggestions=[], path=path)
    posted_date = history.last_post_date(history.load(path))
    assert posted_date is not None

    history.add_post(data, posted=False, angle=None, repos=[], ai_draft="c",
                     final_text="d", visual_suggestions=[], path=path)
    reloaded = history.load(path)
    assert len(reloaded["posts"]) == 2
    assert history.last_post_date(reloaded) == posted_date
    assert reloaded["posts"][1]["id"].endswith("-02")


def test_data_is_gitignored():
    assert "data/" in open(".gitignore").read().splitlines()


# ---------- Feature 3: AI wrapper ----------

def _fake_run(outputs):
    calls = iter(outputs)

    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout=next(calls), stderr="")
    return run


def test_ask_json_handles_code_fences(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run(['```json\n["a", "b"]\n```']))
    assert ai.ask_json("x") == ["a", "b"]


def test_ask_json_retries_once(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run(["not json", '{"ok": true}']))
    assert ai.ask_json("x") == {"ok": True}


def test_ask_json_gives_up_after_two(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run(["nope", "still nope"]))
    with pytest.raises(UserError):
        ai.ask_json("x")


def test_missing_claude_message(monkeypatch):
    monkeypatch.setattr(ai.shutil, "which", lambda _: None)
    with pytest.raises(UserError, match="Claude Code isn't installed"):
        ai.check_installed()


def test_only_ai_module_calls_claude():
    import pathlib
    for f in pathlib.Path("generator").glob("*.py"):
        if f.name != "ai.py":
            assert '"claude"' not in f.read_text(), f"{f} calls claude directly"


# ---------- Feature 2: GitHub ----------

def _response(status=200, body=None, headers=None):
    r = MagicMock()
    r.status_code = status
    r.ok = 200 <= status < 300
    r.json.return_value = body
    r.headers = headers or {}
    return r


def test_repos_skip_forks_and_archived(monkeypatch):
    repos = [{"name": "keep"}, {"name": "fork", "fork": True}, {"name": "old", "archived": True}]
    monkeypatch.setattr(github.requests, "get", lambda *a, **k: _response(body=repos))
    assert [r["name"] for r in github.list_repos("me")] == ["keep"]


def test_commits_all_branches_dedupe_skip_merges(monkeypatch):
    seen_params = []
    shared = {"sha": "s1", "commit": {"message": "Fix navbar\n\nCo-Authored-By: Claude <x>",
                                      "author": {"date": "2026-11-18T00:00:00Z"}}, "html_url": "u1"}
    feature = {"sha": "s2", "commit": {"message": "Add parser", "author": {"date": "2026-11-19T00:00:00Z"}},
               "html_url": "u2"}
    merge = {"sha": "s3", "commit": {"message": "Merge branch 'x'", "author": {"date": "2026-11-19T00:00:00Z"}},
             "html_url": "u3"}

    def get(url, headers, params, timeout):
        if url.endswith("/branches"):
            return _response(body=[{"name": "main"}, {"name": "claude/feature"}])
        seen_params.append(dict(params))
        return _response(body=[shared, merge] if params["sha"] == "main" else [feature, shared])
    monkeypatch.setattr(github.requests, "get", get)

    since = datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)
    commits = github.commits_since("me", "repo", since)
    assert [c["message"] for c in commits] == ["Add parser", "Fix navbar"]
    assert commits[0]["branch"] == "claude/feature"
    assert all(p["since"] == "2026-11-13T10:00:00Z" and "author" not in p for p in seen_params)


def test_quiet_repos_skipped(monkeypatch):
    monkeypatch.setattr(github, "list_repos", lambda u: [
        {"name": "old", "pushed_at": "2026-01-01T00:00:00Z"},
        {"name": "new", "pushed_at": "2026-11-20T00:00:00Z"}])
    called = []
    monkeypatch.setattr(github, "commits_since", lambda u, r, s: called.append(r) or [{"x": 1}])
    activity = github.recent_activity("me", datetime(2026, 11, 13, tzinfo=timezone.utc))
    assert called == ["new"] and list(activity) == ["new"]


def test_rate_limit_message(monkeypatch):
    monkeypatch.setattr(github.requests, "get", lambda *a, **k: _response(
        403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1800000000"}))
    with pytest.raises(UserError, match="rate limit"):
        github.list_repos("me")


def test_no_internet_message(monkeypatch):
    def boom(*a, **k):
        raise github.requests.ConnectionError()
    monkeypatch.setattr(github.requests, "get", boom)
    with pytest.raises(UserError, match="internet"):
        github.list_repos("me")
