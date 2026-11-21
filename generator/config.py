"""Load and validate config.json."""

import json
from pathlib import Path

from generator import UserError

CONFIG_PATH = Path("config.json")

DEFAULTS = {
    "github_username": "",
    "first_run_lookback_days": 7,
    "num_angles": 3,
    "num_commit_questions": 2,
    "linkedin_url": "https://www.linkedin.com/feed/",
    "ai_timeout_seconds": 120,
}


def load_config(path: Path = CONFIG_PATH, ask=input) -> dict:
    """Load the config, creating it with defaults on first run."""
    if path.exists():
        try:
            config = {**DEFAULTS, **json.loads(path.read_text(encoding="utf-8"))}
        except json.JSONDecodeError as e:
            raise UserError(
                f"{path} isn't valid JSON (line {e.lineno}). Fix it, or delete it to start fresh."
            )
    else:
        config = dict(DEFAULTS)

    if not config["github_username"]:
        username = ask("What's your GitHub username? ").strip()
        if not username:
            raise UserError("A GitHub username is needed. Run again and enter it.")
        config["github_username"] = username
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        print(f"Saved settings to {path}.")

    for key in ("first_run_lookback_days", "num_angles", "num_commit_questions", "ai_timeout_seconds"):
        if not isinstance(config[key], int) or config[key] < 0:
            raise UserError(f'"{key}" in {path} must be a whole number of 0 or more.')

    return config
