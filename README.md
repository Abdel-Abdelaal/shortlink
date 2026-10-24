# shortlink

A small URL shortener API built with FastAPI. The app is deliberately simple: the
point of this repo is the engineering around it (branch protection, CI, security
scanning, AI review, and automated deploys), built up one pull request at a time.

CI logic lives in [platform-workflows](https://github.com/Abdel-Abdelaal/platform-workflows)
and is called from here.

## Run it locally

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run fastapi dev src/shortlink/main.py
```

Then open http://127.0.0.1:8000/health or the interactive docs at http://127.0.0.1:8000/docs.

## How changes get in

`main` is protected: no direct pushes, no force pushes, and every change goes
through a pull request with passing checks. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap

- [x] Phase 0: repo foundation (rulesets, templates, PR title check)
- [ ] Phase 1: lint, types, tests, coverage
- [ ] Phase 2: security scanning and supply chain
- [ ] Phase 3: AI pull request review
- [ ] Phase 4: preview and production deploys
- [ ] Phase 5: docs, architecture decisions
