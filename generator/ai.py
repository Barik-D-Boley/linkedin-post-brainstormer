"""All AI calls. Uses Claude Code in headless mode (`claude -p`) through a Claude Pro login.

To swap providers later (e.g. Gemini), only this file should change.
"""

import json
import re
import shutil
import subprocess

from generator import UserError

TIMEOUT = 120


def configure(timeout_seconds: int) -> None:
    global TIMEOUT
    TIMEOUT = timeout_seconds


def check_installed() -> None:
    if shutil.which("claude") is None:
        raise UserError(
            "Claude Code isn't installed (the `claude` command wasn't found).\n"
            "Install it from https://claude.com/claude-code, run `claude` once, "
            "and sign in with your Claude Pro account."
        )


def ask(prompt: str) -> str:
    try:
        result = subprocess.run(
            ["claude", "-p"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=TIMEOUT,
        )
    except FileNotFoundError:
        check_installed()
        raise
    except subprocess.TimeoutExpired:
        raise UserError(
            f"Claude took longer than {TIMEOUT} seconds to answer. "
            'Try again, or raise "ai_timeout_seconds" in config.json.'
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        hint = detail[-1] if detail else "no details"
        raise UserError(
            f"Claude Code returned an error ({hint}).\n"
            "Make sure you're signed in: run `claude` in a terminal and follow the login steps."
        )
    return result.stdout.strip()


def _parse_json(text: str):
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    text = text.strip()
    # Fall back to the first JSON array/object in the text.
    if not text.startswith(("[", "{")):
        match = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
        if match:
            text = match.group(0)
    return json.loads(text)


def ask_json(prompt: str):
    prompt = prompt + "\n\nRespond with valid JSON only. No explanation, no markdown."
    reply = ask(prompt)
    try:
        return _parse_json(reply)
    except json.JSONDecodeError:
        reply = ask(prompt + "\n\nYour last reply wasn't valid JSON. Return ONLY the JSON.")
        try:
            return _parse_json(reply)
        except json.JSONDecodeError:
            raise UserError("Claude didn't return a usable answer twice in a row. Please run it again.")
