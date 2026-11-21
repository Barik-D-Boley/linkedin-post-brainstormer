"""Read and write the local post history (data/history.json)."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from generator import UserError

HISTORY_PATH = Path("data/history.json")


def now() -> datetime:
    return datetime.now().astimezone()


def load(path: Path = HISTORY_PATH) -> dict:
    if not path.exists():
        return {"posts": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise UserError(f"{path} is damaged (not valid JSON). Restore a backup or delete it to start over.")
    data.setdefault("posts", [])
    return data


def save(data: dict, path: Path = HISTORY_PATH) -> None:
    """Write atomically: temp file in the same folder, then rename over the original."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def last_post_date(data: dict) -> datetime | None:
    dates = [datetime.fromisoformat(p["created_at"]) for p in data["posts"] if p.get("posted")]
    return max(dates) if dates else None


def since_date(data: dict, lookback_days: int) -> datetime:
    """When to start looking for commits: the last real post, or the first-run lookback."""
    return last_post_date(data) or (now() - timedelta(days=lookback_days))


def new_id(data: dict, when: datetime) -> str:
    day = when.strftime("%Y-%m-%d")
    count = sum(1 for p in data["posts"] if p.get("id", "").startswith(day))
    return f"{day}-{count + 1:02d}"


def add_post(data: dict, *, posted: bool, angle: dict | None, repos: list[str],
             ai_draft: str, final_text: str, visual_suggestions: list[str],
             path: Path = HISTORY_PATH) -> dict:
    when = now()
    post = {
        "id": new_id(data, when),
        "created_at": when.isoformat(timespec="seconds"),
        "posted": posted,
        "angle": angle,
        "repos": repos,
        "ai_draft": ai_draft,
        "final_text": final_text,
        "visual_suggestions": visual_suggestions,
    }
    data["posts"].append(post)
    save(data, path)
    return post
