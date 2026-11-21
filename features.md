# Features: LinkedIn Post Brainstormer

Detailed specs for building the tool. See `README.md` for the overview.

**How to use this file:** Build one feature at a time, in the order listed under [Build order](#build-order). Each feature ends with acceptance criteria. A feature is done when every one of its criteria passes. When a feature is done, check it off in the README roadmap.

---

## General rules

- **Language:** Python 3.10+. Keep dependencies small: `requests`, `pyperclip`, and the standard library.
- **Interface:** Terminal only. Clear prompts, numbered choices, and Enter to skip optional questions.
- **One entry point:** `python run.py` runs the whole weekly flow.
- **Private data stays local:** The `data/` folder (post history) is in `.gitignore`, because the repo is public.
- **The AI can be swapped:** All AI calls go through one module (`ai.py`), so switching from Claude Code to Gemini later only touches that file.
- **Fail gracefully:** If something fails (no internet, Claude Code isn't installed, the GitHub rate limit is hit), print a plain-English message saying what went wrong and how to fix it. Never show a raw stack trace.

## Suggested file layout

```
run.py                  # entry point, runs the weekly flow
config.json             # user settings
generator/
    config.py           # load and validate config
    history.py          # read/write post history
    github.py           # fetch repos and commits
    ai.py               # all AI calls (Claude Code headless)
    prompts.py          # prompt templates
    flow.py             # the step-by-step weekly flow
data/
    history.json        # post history (git-ignored)
tests/
```

## Config: `config.json`

```json
{
  "github_username": "Barik-D-Boley",
  "first_run_lookback_days": 7,
  "num_angles": 3,
  "num_commit_questions": 2,
  "linkedin_url": "https://www.linkedin.com/feed/",
  "ai_timeout_seconds": 120
}
```

- If `config.json` is missing, create it with the defaults above and ask for the GitHub username.
- An optional `GITHUB_TOKEN` environment variable raises the GitHub rate limit, but the tool must work without it.

---

## Feature 1: Post history

Stores every post so the tool knows when I last posted and has my past writing to learn from.

**File:** `data/history.json`

```json
{
  "posts": [
    {
      "id": "2026-11-20-01",
      "created_at": "2026-11-20T17:30:00-07:00",
      "posted": true,
      "angle": {
        "type": "lesson",
        "title": "What I learned switching to Tailwind"
      },
      "repos": ["portfolio-website"],
      "ai_draft": "First draft text the AI wrote...",
      "final_text": "The version I actually posted...",
      "visual_suggestions": ["Before/after screenshot of the site"]
    }
  ]
}
```

**Behavior:**
- `last_post_date()` returns the `created_at` of the most recent post where `posted` is `true`.
- If no post has been made yet (first run), go back `first_run_lookback_days` from today.
- Save posts I don't publish with `posted: false`. They don't move the last post date.
- Create the file and the `data/` folder if they don't exist.
- Write safely (write to a temp file, then rename) so a crash can't corrupt the history.

**Acceptance criteria:**
- [ ] On first run, with no history file, the lookback falls back to the configured number of days.
- [ ] After a post is saved with `posted: true`, the next run uses its date.
- [ ] Unposted drafts are saved but don't change the last post date.
- [ ] `data/` is in `.gitignore`.

---

## Feature 2: GitHub activity

Pulls what I've worked on since my last post.

**Behavior:**
- List my public repos: `GET /users/{username}/repos?type=owner&per_page=100`.
  - Skip forks and archived repos.
- Skip repos whose `pushed_at` is older than the last post date (saves API calls).
- For each remaining repo, list its branches, then get commits since the last post date on **every branch**: `GET /repos/{username}/{repo}/commits?since={ISO date}&sha={branch}`. Unmerged PR branches (e.g. from Claude Code) count.
  - No author filter: commits made by Claude Code or other tools may not be authored under my account.
  - Remove duplicate commits that appear on more than one branch.
  - Skip merge commits (messages starting with "Merge") and strip trailer lines like `Co-Authored-By`.
- For each commit, keep the repo name, date, commit message (full, not just the first line) and URL.
- Group the results by repo and print a short summary, for example:
  `portfolio-website: 12 commits | python-toolkit: 3 commits`.
- If there are no commits, say so and continue. The post can still be based on the weekly questions alone.

**Acceptance criteria:**
- [ ] Works without a GitHub token.
- [ ] Forks, archived repos and merge commits are left out.
- [ ] Only commits after the last post date are included, from all branches, without duplicates.
- [ ] Hitting the rate limit or having no internet gives a clear message instead of a crash.

---

## Feature 3: AI wrapper (`ai.py`)

A single function every other feature uses to talk to the AI.

**Behavior:**
- `ask(prompt: str) -> str` runs `claude -p` through `subprocess`, passes the prompt on stdin, and returns the response text.
- `ask_json(prompt: str) -> dict | list` asks for JSON only and parses the response. If parsing fails, it retries once with a reminder to return valid JSON, then raises a clear error.
- Uses `ai_timeout_seconds` from the config.
- On startup, checks that the `claude` command exists. If it doesn't, explain how to install Claude Code and sign in with a Pro account.

**Acceptance criteria:**
- [ ] A simple prompt returns text.
- [ ] `ask_json` handles a response wrapped in markdown code fences.
- [ ] A missing `claude` command gives a helpful message.
- [ ] No other module calls `claude` directly.

---

## Feature 4: Weekly questions

Fills in what commits can't show: what I learned, what was hard and what I finished.

**A mixed set of questions:**

*Fixed questions (the same every week):*
1. What was the hardest part of your week, technically or otherwise?
2. What's something you learned that you didn't know last week?
3. Did you finish anything, or reach a milestone you're proud of?

*Commit questions (written by the AI each week):*
- The AI looks at the commits and writes `num_commit_questions` (default 2) specific follow-up questions. For example: "You made 9 commits to the navbar on portfolio-website. What was going wrong with it?"
- These questions should look for the story behind the commits (a problem, a decision, a surprise), not ask me to list features.
- If there are no commits, skip the commit questions.

**Behavior:**
- Ask the questions one at a time. Pressing Enter skips a question.
- Keep the answers for the next steps.

**Acceptance criteria:**
- [ ] All 3 fixed questions are asked every run.
- [ ] Commit questions mention specific repos or work from that week's commits.
- [ ] Skipped questions are left out of later prompts, not sent as empty answers.

---

## Feature 5: Post angles

Suggests what the post could be about.

**Behavior:**
- Send the AI the commits and my answers. It returns `num_angles` (default 3) angles as JSON:

```json
[
  {
    "type": "lesson | challenge | finished_project",
    "title": "Short title",
    "summary": "1–2 sentences on what the post would say",
    "based_on": "Which answers or commits it comes from"
  }
]
```

- Angles must focus on lessons, challenges or finished projects. **Never a list of features.**
- Show the angles numbered. I can:
  - Pick one by number.
  - Type `c` to describe my own angle.
  - Type `r` to get new suggestions.

**Acceptance criteria:**
- [ ] Every angle has one of the three allowed types.
- [ ] None of the angles is a list of features.
- [ ] The custom angle and regenerate options both work.

---

## Feature 6: Draft and revise

Writes the post and lets me shape it.

**Writing guidelines (go in the prompt):**
- First person, in a natural, conversational tone. It should sound like a student sharing what they learned, not a corporate announcement.
- Open with a strong first line, because LinkedIn hides everything after the first 2–3 lines behind "see more".
- About 100–250 words.
- Short paragraphs. Use a list only if it really helps.
- No more than 3 hashtags, at the end. Few or no emojis.
- Link the repo where it fits.
- No overused AI phrases ("I'm thrilled to announce", "game-changer", "delve", etc.).

**Revise loop:**
After showing the draft, offer:
- `a`: Accept
- `r`: Revise. I type feedback ("shorter", "less formal", "mention the bug I fixed"), and the AI rewrites the draft.
- `e`: Edit directly. Open the draft in my text editor (`$EDITOR`, or the system default), then reload it.
- `q`: Quit and save as an unposted draft.

Keep looping until I accept or quit. Keep the first AI draft as `ai_draft`, for learning my voice later.

**Acceptance criteria:**
- [ ] Drafts follow the guidelines (length, hashtag limit, strong opening).
- [ ] Revisions use my feedback and keep the parts I didn't ask to change.
- [ ] Edits made directly in my editor are kept.
- [ ] Quitting saves the draft with `posted: false`.

---

## Feature 7: Visual suggestions

**Behavior:**
- After I accept the post, the AI suggests 2–3 specific images or videos to go with it, based on the post and the repos it mentions. Each suggestion is one line saying what to capture.
  - Good: "GIF of the project modal opening and closing on mobile."
  - Bad: "An image related to your project."
- I can skip this step.

**Acceptance criteria:**
- [ ] Suggestions are specific to the post, not generic.
- [ ] They're saved to the history.

---

## Feature 8: Hand-off

**Behavior:**
1. Copy the final text to the clipboard (`pyperclip`).
2. Open `linkedin_url` in the default browser (`webbrowser`).
3. Print: "Copied to clipboard. Paste it into LinkedIn, add your visual, and post."
4. Ask: "Did you post it? (y/n)"
   - `y`: Save with `posted: true`. This becomes the new last post date.
   - `n`: Save with `posted: false`.

**Acceptance criteria:**
- [ ] The text is on the clipboard and LinkedIn opens.
- [ ] Only a confirmed post updates the last post date.
- [ ] If copying to the clipboard fails, print the text so I can copy it by hand.

---

## Build order

1. Config + Feature 1 (post history)
2. Feature 3 (AI wrapper). Test it on its own before building anything on top of it.
3. Feature 2 (GitHub activity)
4. Feature 4 (weekly questions)
5. Feature 5 (post angles)
6. Feature 6 (draft and revise)
7. Feature 7 (visual suggestions)
8. Feature 8 (hand-off)
9. Connect everything in `flow.py` and `run.py`, then do a full test run.

---

## v2 (later; don't build yet)

- **Learn my voice:** Put my last 3–5 `final_text` posts in the draft prompt as style examples. Compare `ai_draft` with `final_text` to see what I usually change.
- **Filter out commit noise:** Before suggesting angles, ignore small commits (typos, formatting, README tweaks).
- **Gemini fallback:** Add Gemini API free-tier support to `ai.py`, chosen in the config.
- **Repos I haven't posted about:** Point out repos or milestones that have never appeared in a post.
