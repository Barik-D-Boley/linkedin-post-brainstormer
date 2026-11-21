# LinkedIn Post Brainstormer

A weekly Python tool that turns my GitHub activity and what I've learned into LinkedIn post drafts. I edit each draft until I'm happy with it, and the tool gets it ready to post.

> **Note:** I now run this workflow as a weekly Claude scheduled task, so I can answer the questions and revise drafts from my phone. This repo is a complete, working v1 of the tool.

## Why

I want to post on LinkedIn consistently about what I'm building and learning, but writing a post from scratch every week takes time and it's easy to skip. This tool does the first draft so all I have to do each week is react and edit.

The goal is **not** a feature dump. Good posts focus on:

- Things I learned
- Challenges I worked through
- Projects I finished

## How it works

I run the script once a week when my reminder goes off. It walks me through this flow:

1. **Check history:** Read my local post history to find the date of my last post.
2. **Gather activity:** Pull commits from my public GitHub repos since that date.
3. **Ask me questions:** A few short prompts to fill in what commits can't show, such as:
   - What was the hardest part of this week?
   - What did you learn?
   - Did you finish anything?
4. **Suggest angles:** Propose 2–3 post ideas built around a lesson, a challenge or a finished project. I pick one or describe my own.
5. **Draft:** Generate the post text in my voice.
6. **Revise:** I ask for changes until the draft is right, or edit it directly.
7. **Suggest a visual:** Recommend an image or video to go with the post (a screenshot, before/after, diagram, GIF of the project working, etc.).
8. **Hand off:** Copy the final text to my clipboard, open LinkedIn in my browser, and save the post to my history.

I post on LinkedIn myself. The tool never connects to my LinkedIn account.

## Learning my voice

Every time I finish a post, the tool saves both its original draft and my final edited version. Future drafts use my recent finished posts as examples, so the writing should sound more like me over time.

## Tech stack

| Part | Tool |
|---|---|
| Language | Python 3 |
| AI | [Claude Code](https://claude.com/claude-code) in headless mode (`claude -p`) through my Claude Pro subscription. No API key or per-token cost. |
| GitHub data | GitHub REST API (public repos, no token needed) |
| Post history | Local JSON file |
| Hand-off | Clipboard copy + opens LinkedIn in the default browser |

## Setup

1. Install Python 3.10+ and [Claude Code](https://claude.com/claude-code). Run `claude` once and sign in with your Claude Pro account.
2. Clone this repo and install the dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set your GitHub username in `config.json` (or delete the file and the script will ask).
4. Run it:
   ```
   python run.py
   ```

Optional: set a `GITHUB_TOKEN` environment variable for a higher GitHub rate limit. To edit drafts in a specific editor, set `EDITOR` (e.g. `code --wait`); otherwise your system's default text editor opens.

Your post history is saved in `data/history.json`, which is git-ignored.

### Tests
```
python -m pytest
```

## Roadmap

### v1: Core weekly flow
- [x] Post history file (last post date, past drafts and finals)
- [x] Pull commits from public repos since the last post
- [x] Weekly reflection questions
- [x] Suggest 2–3 post angles
- [x] Draft and revise loop
- [x] Image or video suggestion
- [x] Copy to clipboard and open LinkedIn

### v2: Improvements
- [ ] Use past finished posts as voice examples
- [ ] Filter out small or noisy commits (typos, formatting) before suggesting angles
- [ ] Gemini API free tier as a fallback AI
- [ ] Suggest which repos or milestones haven't been posted about yet

## Status

v1 complete and tested. Detailed specs for each feature are in [`features.md`](features.md).
