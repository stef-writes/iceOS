# Developer Workflow 🚀

> TL;DR: `make lint type test`, commit, push – the tooling does the rest.

This document captures the **daily loop** you'll follow when working on iceOS.
It mirrors what was explained in chat so nobody has to scroll through history.

---

## 0. First-time setup (per machine)

```bash
# clone & enter repo
$ git clone https://github.com/your-org/iceOS.git && cd iceOS

# install core + dev dependencies
$ make install

# enable pre-commit hooks
$ pre-commit install
```

> The hooks will auto-format/lint each commit; CI enforces the same checks.

---

## 1. Start a task

```bash
$ git checkout -b feat/<short-slug>   # create feature branch
$ git pull origin main --rebase       # ensure you're up-to-date

# optional sanity
$ make doctor                         # run full healthchecks locally
```

---

## 2. Code / docs / tests

• Follow rules in `.cursorrules` (type-hints, Pydantic, async, no cross-layer imports).  
• Update / add tests under `tests/`.  
• Write or update docstrings for any public API you touch.  
• Added a Tool / Node / Agent / Chain?  Run:

```bash
$ make refresh-docs   # regenerates CAPABILITY_CATALOG & CODEBASE_OVERVIEW
```

---

## 3. Fast local feedback

```bash
$ make lint     # ruff + isort
$ make type     # mypy
$ make test     # pytest
```
All green? Proceed.  
Red? Fix and repeat 🔄.

---

## 4. Commit

```bash
$ git add -p          # stage selectively
$ git commit -m "feat: brief description"
```
The pre-commit stack runs automatically:
ruff → black → isort → pyupgrade → mypy → pydocstyle.  
Any failure blocks the commit.

---

## 5. Push & Pull Request

```bash
$ git push -u origin feat/<slug>
```
Open the PR; GitHub Actions executes:
1. `make refresh-docs`  
2. `make lint`  
3. `make type`  
4. `make test`

Green ✔️ = ready to merge.  
Red ❌ = click the failing job → logs; reproduce locally if needed.

---

## 6. Merge & cleanup

```bash
$ git checkout main && git pull
$ git branch -d feat/<slug>
```

---

## 7. FYI: where artifacts live & what's ignored

Tracked in Git:
• Top-level generated docs (`CODEBASE_OVERVIEW.md`, `CAPABILITY_CATALOG.json`) – they feed Cursor context.

Ignored via `.gitignore`:
• Virtual envs (`.venv/`, `venv/`, `.env/`).  
• Build artefacts (`build/`, `dist/`, `*.egg-info/`).  
• Test caches (`.pytest_cache/`, `.coverage`, `htmlcov/`).  
• Tool caches (`.mypy_cache/`, `.ruff_cache/`).  
• IDE clutter (`.vscode/`, `.idea/`).

If you see new local artefacts polluting `git status`, add them to `.gitignore`.

---

Happy hacking! ✨ 