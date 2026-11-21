# CLAUDE.md

## Before working
- Read `README.md` (what the tool does) and `features.md` (detailed specs).
- Build one feature at a time, in the order in `features.md` → "Build order".
- A feature is done only when every acceptance criterion in `features.md` passes.
- When a feature is done, check it off in the README roadmap.

## Rules
- Python 3.10+. Dependencies: `requests`, `pyperclip`, the standard library. Ask before adding others.
- All AI calls go through `generator/ai.py`. Nothing else calls `claude` directly.
- Never commit `data/` (it holds private post history).
- Errors shown to the user are plain English with a fix, never raw stack traces.
- Keep v2 features (listed at the bottom of `features.md`) out until v1 is done.

## Testing
- `python -m pytest`
- Tests must not call the real AI or GitHub. Mock `generator.ai` and `generator.github`.
