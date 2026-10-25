---
status: accepted
date: 2026-10-25
---

# Run PR-Agent next to the isolated reviewer, on shortlink only

## Context and problem statement

The fleet's AI review is a custom runner in platform-workflows. It exists because
off-the-shelf review bots run the model call and the GitHub token in one process,
while PR text is untrusted input to the model. The owner asked whether existing
tools such as Cursor Bugbot could do this job instead.

## Considered options

- **Cursor Bugbot:** needs a paid Cursor plan; can't use the MiMo key.
- **GitHub Copilot code review:** needs a Copilot plan.
- **CodeRabbit:** free for public repos, but uses its own models and needs a GitHub
  App install by the owner.
- **PR-Agent** (The-PR-Agent/pr-agent, open source): works with any
  OpenAI-compatible endpoint, so it can use the same MiMo Flash key.
- **Keep only the isolated runner.**

## Trial (shortlink PR 14)

Both reviewers ran on the PR that added the trial, with the same model and key.

| | Isolated runner | PR-Agent |
| --- | --- | --- |
| Ran on first attempt | yes | yes |
| Real finding only it caught | comment pointed at an ADR that didn't exist | Dependabot skip used `github.actor`, bypassable by a human push |
| Shared false alarm | "missing checkout" (PR-Agent reads the diff via API) | same |
| Output | one summary, Conventional Comments, neutral check | review guide plus scored code suggestions with diffs |
| GitHub token in model process | no | yes (`issues`/`pull-requests: write`) |

## Decision outcome

Keep both, advisory, with PR-Agent limited to shortlink. They found different real
issues on the same diff, so together they cover more. PR-Agent's suggestions
are easier to act on. The isolated runner stays the fleet default, because
it never gives the model process a GitHub token.

### Consequences

- Good: two independent reviews; existing tooling used where it fits.
- Bad: on shortlink, a prompt-injected PR could steer PR-Agent's comments. The
  token can't merge, approve or push code (`contents: read`), but it can post
  comments. Forks and Dependabot PRs never run it.
- Revisit after a month of PRs. Widen it to the fleet only if its findings keep
  outperforming the isolated runner's.

### Immutable runtime

The upstream action source was pinned to v0.47.0, but its Dockerfile fetched the
mutable `github_action` container tag. The trial now uses the reviewed platform
adapter, whose Dockerfile selects the published v0.47.0 image by full manifest
digest and invokes the upstream GitHub entrypoint. See the
[adapter provenance and upstream licensing](https://github.com/Abdel-Abdelaal/platform-workflows/tree/f60efba792d811aa8a848cc465c3ae20523fdf14/actions/pr-agent).
This preserves the existing co-located credential trade-off. It does not add the
isolated runner's full telemetry to PR-Agent.
