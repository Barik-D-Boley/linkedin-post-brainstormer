"""The step-by-step weekly flow."""

import os
import platform
import subprocess
import tempfile
import webbrowser
from pathlib import Path

from generator import UserError, ai, github, history, prompts

LINE = "-" * 60


def header(title: str) -> None:
    print(f"\n{LINE}\n{title}\n{LINE}")


# ---------- Feature 4: weekly questions ----------

def ask_questions(activity: dict, activity_text: str, n_commit_q: int, ask=input) -> list[dict]:
    questions = list(prompts.FIXED_QUESTIONS)
    if activity and n_commit_q > 0:
        generated = ai.ask_json(prompts.commit_questions(activity_text, n_commit_q))
        if isinstance(generated, list):
            questions += [str(q) for q in generated[:n_commit_q]]

    header("This week's questions (press Enter to skip any)")
    answers = []
    for i, q in enumerate(questions, 1):
        print(f"\n{i}. {q}")
        answers.append({"question": q, "answer": ask("> ").strip()})
    return answers


# ---------- Feature 5: post angles ----------

def _clean_angles(raw) -> list[dict]:
    if not isinstance(raw, list):
        return []
    cleaned = []
    for a in raw:
        if isinstance(a, dict) and a.get("type") in prompts.ANGLE_TYPES and a.get("title"):
            cleaned.append({
                "type": a["type"],
                "title": str(a["title"]),
                "summary": str(a.get("summary", "")),
                "based_on": str(a.get("based_on", "")),
            })
    return cleaned


def choose_angle(activity_text: str, answers_text: str, n: int, ask=input) -> dict:
    while True:
        angles = _clean_angles(ai.ask_json(prompts.angles(activity_text, answers_text, n)))
        if not angles:
            print("Claude didn't return usable angles. Trying again...")
            angles = _clean_angles(ai.ask_json(prompts.angles(activity_text, answers_text, n)))
        header("Post ideas")
        for i, a in enumerate(angles, 1):
            label = a["type"].replace("_", " ")
            print(f"\n{i}. [{label}] {a['title']}\n   {a['summary']}")
        print("\nPick a number, 'c' to describe your own angle, or 'r' for new ideas.")
        while True:
            choice = ask("> ").strip().lower()
            if choice == "r":
                break
            if choice == "c":
                title = ask("What should the post be about? ").strip()
                if title:
                    return {"type": "custom", "title": title, "summary": "", "based_on": "user"}
                continue
            if choice.isdigit() and 1 <= int(choice) <= len(angles):
                return angles[int(choice) - 1]
            print(f"Enter 1-{len(angles)}, 'c', or 'r'.")


# ---------- Feature 6: draft and revise ----------

def edit_in_editor(text: str, ask=input) -> str:
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="linkedin-post-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        editor = os.environ.get("EDITOR")
        if editor:
            subprocess.run([*editor.split(), path])
        else:
            system = platform.system()
            if system == "Windows":
                os.startfile(path)  # type: ignore[attr-defined]
            elif system == "Darwin":
                subprocess.run(["open", "-t", path])
            else:
                subprocess.run(["xdg-open", path])
            ask("Edit the post, save the file, then press Enter here... ")
        return Path(path).read_text(encoding="utf-8").strip()
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def draft_and_revise(angle: dict, activity_text: str, answers_text: str, ask=input,
                     editor=edit_in_editor) -> tuple[str, str, bool]:
    """Returns (ai_draft, final_text, accepted)."""
    print("\nWriting a draft...")
    ai_draft = ai.ask(prompts.draft(angle, activity_text, answers_text))
    current = ai_draft
    while True:
        header("Draft")
        print(current)
        print(f"\n({len(current.split())} words)")
        print("\n[a] accept  [r] revise with feedback  [e] edit it yourself  [q] quit and save as draft")
        choice = ask("> ").strip().lower()
        if choice == "a":
            return ai_draft, current, True
        if choice == "q":
            return ai_draft, current, False
        if choice == "r":
            feedback = ask("What should change? ").strip()
            if feedback:
                print("Revising...")
                current = ai.ask(prompts.revise(current, feedback))
        elif choice == "e":
            edited = editor(current, ask)
            if edited:
                current = edited
        else:
            print("Enter a, r, e, or q.")


# ---------- Feature 7: visual suggestions ----------

def suggest_visuals(post: str, repos: list[str], ask=input) -> list[str]:
    if ask("\nWant ideas for an image or video to go with it? (y/n) ").strip().lower() != "y":
        return []
    raw = ai.ask_json(prompts.visuals(post, repos))
    ideas = [str(x) for x in raw] if isinstance(raw, list) else []
    header("Visual ideas")
    for idea in ideas:
        print(f"- {idea}")
    return ideas


# ---------- Feature 8: hand-off ----------

def copy_to_clipboard(text: str) -> bool:
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def hand_off(text: str, linkedin_url: str, ask=input,
             copy=copy_to_clipboard, open_url=webbrowser.open) -> bool:
    if copy(text):
        print("\nCopied to clipboard. Paste it into LinkedIn, add your visual, and post.")
    else:
        print("\nCouldn't copy to the clipboard, so here's the text to copy by hand:\n")
        print(text)
        print()
    try:
        open_url(linkedin_url)
    except Exception:
        print(f"Open LinkedIn here: {linkedin_url}")
    while True:
        answer = ask("Did you post it? (y/n) ").strip().lower()
        if answer in ("y", "n"):
            return answer == "y"


# ---------- Full weekly flow ----------

def repos_for_post(activity: dict, text: str, angle: dict) -> list[str]:
    haystack = f"{text} {angle.get('title', '')} {angle.get('based_on', '')}".lower()
    mentioned = [r for r in activity if r.lower() in haystack]
    return mentioned or list(activity)


def run(config: dict, ask=input) -> None:
    ai.configure(config["ai_timeout_seconds"])
    ai.check_installed()
    username = config["github_username"]

    data = history.load()
    since = history.since_date(data, config["first_run_lookback_days"])
    last = history.last_post_date(data)
    header("LinkedIn Post Brainstormer")
    print(f"Looking at commits since {'your last post' if last else 'your first run'} "
          f"({since.strftime('%b %d, %Y')})...")

    activity = github.recent_activity(username, since)
    print(github.summary_line(activity))
    activity_text = prompts.format_activity(activity, username)

    answers = ask_questions(activity, activity_text, config["num_commit_questions"], ask)
    answers_text = prompts.format_answers(answers)
    if not activity and answers_text == "(No answers given.)":
        print("\nNo commits and no answers, so there's nothing to post about yet. Try again later!")
        return

    print("\nComing up with post ideas...")
    angle = choose_angle(activity_text, answers_text, config["num_angles"], ask)
    ai_draft, final_text, accepted = draft_and_revise(angle, activity_text, answers_text, ask)
    repos = repos_for_post(activity, final_text, angle)

    if not accepted:
        history.add_post(data, posted=False, angle=angle, repos=repos, ai_draft=ai_draft,
                         final_text=final_text, visual_suggestions=[])
        print("\nSaved as an unposted draft in data/history.json.")
        return

    visuals = suggest_visuals(final_text, repos, ask)
    posted = hand_off(final_text, config["linkedin_url"], ask)
    history.add_post(data, posted=posted, angle=angle, repos=repos, ai_draft=ai_draft,
                     final_text=final_text, visual_suggestions=visuals)
    print("\nSaved. " + ("Nice work, see you next week!" if posted
                         else "It's saved as a draft and won't count as your last post."))
