from datetime import datetime, timezone

import pytest

from generator import flow, history, prompts


def answers_from(seq):
    it = iter(seq)
    return lambda _prompt="": next(it)


ACTIVITY = {"portfolio-website": [{"repo": "portfolio-website", "date": "2026-11-18T00:00:00Z",
                                   "message": "Fix navbar on mobile", "url": ""}]}


# ---------- Feature 4 ----------

def test_questions_mixed(monkeypatch):
    monkeypatch.setattr(flow.ai, "ask_json", lambda p: ["Why the navbar on portfolio-website?", "Q2"])
    got = flow.ask_questions(ACTIVITY, "text", 2, ask=answers_from(["a1", "", "a3", "a4", ""]))
    assert [a["question"] for a in got[:3]] == prompts.FIXED_QUESTIONS
    assert "portfolio-website" in got[3]["question"]
    assert len(got) == 5


def test_no_commit_questions_without_commits(monkeypatch):
    monkeypatch.setattr(flow.ai, "ask_json", lambda p: pytest.fail("shouldn't ask AI"))
    got = flow.ask_questions({}, "text", 2, ask=answers_from(["", "", ""]))
    assert len(got) == 3


def test_skipped_answers_left_out():
    text = prompts.format_answers([{"question": "Q1", "answer": ""}, {"question": "Q2", "answer": "yes"}])
    assert "Q1" not in text and "Q2" in text


# ---------- Feature 5 ----------

ANGLES = [
    {"type": "lesson", "title": "L", "summary": "s"},
    {"type": "feature_list", "title": "bad"},
    {"type": "challenge", "title": "C", "summary": "s"},
]


def test_angles_filter_bad_types(monkeypatch):
    monkeypatch.setattr(flow.ai, "ask_json", lambda p: ANGLES)
    angle = flow.choose_angle("a", "b", 3, ask=answers_from(["2"]))
    assert angle["title"] == "C"


def test_custom_and_regenerate(monkeypatch):
    calls = []
    monkeypatch.setattr(flow.ai, "ask_json", lambda p: calls.append(1) or ANGLES)
    angle = flow.choose_angle("a", "b", 3, ask=answers_from(["r", "c", "My own idea"]))
    assert angle == {"type": "custom", "title": "My own idea", "summary": "", "based_on": "user"}
    assert len(calls) == 2


# ---------- Feature 6 ----------

def test_revise_then_edit_then_accept(monkeypatch):
    replies = iter(["first draft", "shorter draft"])
    monkeypatch.setattr(flow.ai, "ask", lambda p: next(replies))
    ai_draft, final, accepted = flow.draft_and_revise(
        {"title": "t"}, "a", "b",
        ask=answers_from(["r", "shorter", "e", "a"]),
        editor=lambda text, ask: text + " (my edit)",
    )
    assert ai_draft == "first draft"
    assert final == "shorter draft (my edit)"
    assert accepted


def test_quit_returns_not_accepted(monkeypatch):
    monkeypatch.setattr(flow.ai, "ask", lambda p: "draft")
    _, _, accepted = flow.draft_and_revise({"title": "t"}, "a", "b", ask=answers_from(["q"]))
    assert not accepted


def test_guidelines_in_draft_prompt():
    p = prompts.draft({"title": "t", "type": "lesson"}, "a", "b")
    assert "3 hashtags" in p and "100-250 words" in p and "first line" in p


# ---------- Feature 8 ----------

def test_handoff_clipboard_and_browser():
    copied, opened = [], []
    posted = flow.hand_off("post", "https://x", ask=answers_from(["y"]),
                           copy=lambda t: copied.append(t) or True, open_url=opened.append)
    assert posted and copied == ["post"] and opened == ["https://x"]


def test_handoff_clipboard_fallback_prints(capsys):
    flow.hand_off("THE POST", "https://x", ask=answers_from(["n"]),
                  copy=lambda t: False, open_url=lambda u: None)
    assert "THE POST" in capsys.readouterr().out


# ---------- Full flow ----------

def test_full_run_only_confirmed_post_moves_date(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(flow.ai, "check_installed", lambda: None)
    monkeypatch.setattr(flow.github, "recent_activity", lambda u, s: ACTIVITY)
    monkeypatch.setattr(flow.ai, "ask", lambda p: "Post about portfolio-website navbar.")
    json_replies = iter([
        ["Q about portfolio-website?", "Q2?"],          # commit questions
        [{"type": "challenge", "title": "Navbar", "summary": "s"}],  # angles
        ["Screenshot of the navbar"],                 # visuals
    ])
    monkeypatch.setattr(flow.ai, "ask_json", lambda p: next(json_replies))
    monkeypatch.setattr(flow, "copy_to_clipboard", lambda t: True)
    monkeypatch.setattr(flow.webbrowser, "open", lambda u: None)

    config = {"github_username": "me", "first_run_lookback_days": 7, "num_angles": 3,
              "num_commit_questions": 2, "linkedin_url": "https://x", "ai_timeout_seconds": 5}
    flow.run(config, ask=answers_from(["hard", "learned", "", "a", "b", "1", "a", "y", "n"]))

    data = history.load()
    post = data["posts"][0]
    assert post["posted"] is False
    assert post["repos"] == ["portfolio-website"]
    assert post["visual_suggestions"] == ["Screenshot of the navbar"]
    assert history.last_post_date(data) is None
