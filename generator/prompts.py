"""Prompt templates. Every prompt the tool sends lives here."""

ANGLE_TYPES = ("lesson", "challenge", "finished_project")

FIXED_QUESTIONS = [
    "What was the hardest part of your week, technically or otherwise?",
    "What's something you learned that you didn't know last week?",
    "Did you finish anything, or reach a milestone you're proud of?",
]

WRITING_GUIDELINES = """\
- First person, natural and conversational: a student sharing what they learned, not a corporate announcement.
- Open with a strong first line. LinkedIn hides everything after the first 2-3 lines behind "see more".
- About 100-250 words.
- Short paragraphs. Use a list only if it truly helps.
- At most 3 hashtags, at the very end. Few or no emojis.
- Link the GitHub repo where it fits naturally.
- Never use overused AI phrases ("I'm thrilled to announce", "game-changer", "delve", "excited to share", "journey", etc.).
- Focus on the lesson, challenge, or finished result. Never a list of features."""


def format_activity(activity: dict[str, list[dict]], username: str, max_chars: int = 6000) -> str:
    if not activity:
        return "(No commits this period.)"
    lines = []
    for repo, commits in activity.items():
        lines.append(f"Repo: {repo} (https://github.com/{username}/{repo}) - {len(commits)} commits")
        for c in commits:
            msg = c["message"].replace("\n", " / ")
            lines.append(f"  - {c['date'][:10]}: {msg[:300]}")
    text = "\n".join(lines)
    return text if len(text) <= max_chars else text[:max_chars] + "\n  ... (more commits trimmed)"


def format_answers(answers: list[dict]) -> str:
    answered = [a for a in answers if a["answer"].strip()]
    if not answered:
        return "(No answers given.)"
    return "\n".join(f"Q: {a['question']}\nA: {a['answer']}" for a in answered)


def commit_questions(activity_text: str, n: int) -> str:
    return f"""You're helping a student turn their week of coding into a LinkedIn post.
Here are their GitHub commits since their last post:

{activity_text}

Write {n} short, specific follow-up questions about this work. Each question must mention a
specific repo or piece of work from the commits. Look for the story behind the commits: a problem
they hit, a decision they made, something that surprised them. Do NOT ask them to list features.

Return a JSON array of {n} strings."""


def angles(activity_text: str, answers_text: str, n: int) -> str:
    return f"""You're helping a student decide what to post on LinkedIn this week.

Their GitHub commits since their last post:
{activity_text}

Their answers to this week's reflection questions:
{answers_text}

Suggest {n} different post angles. Each must be one of these types:
- "lesson": something they learned
- "challenge": a problem they worked through
- "finished_project": something they completed
Never suggest a list of features.

Return a JSON array where each item is:
{{"type": "lesson" | "challenge" | "finished_project",
  "title": "short title",
  "summary": "1-2 sentences on what the post would say",
  "based_on": "which answers or commits it comes from"}}"""


def draft(angle: dict, activity_text: str, answers_text: str) -> str:
    return f"""Write a LinkedIn post for a student, in their voice.

Chosen angle ({angle.get('type', 'custom')}): {angle['title']}
{angle.get('summary', '')}

Background - their GitHub commits:
{activity_text}

Background - their own words about the week:
{answers_text}

Writing guidelines:
{WRITING_GUIDELINES}

Only use facts from the background above; don't invent results or numbers.
Return only the post text, nothing else."""


def revise(current: str, feedback: str) -> str:
    return f"""Here is a LinkedIn post draft:

---
{current}
---

Revise it based on this feedback: {feedback}

Keep everything the feedback doesn't ask to change. Still follow these guidelines:
{WRITING_GUIDELINES}

Return only the revised post text, nothing else."""


def visuals(post: str, repos: list[str]) -> str:
    repo_list = ", ".join(repos) if repos else "(none)"
    return f"""Here is a LinkedIn post about a student's project work:

---
{post}
---

Repos involved: {repo_list}

Suggest 3 specific images or short videos they could capture to go with this post.
Each should say exactly what to capture, e.g. "GIF of the project modal opening and closing on
mobile", not something generic like "an image of your project".

Return a JSON array of 3 strings."""
