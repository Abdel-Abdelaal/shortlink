# Contributing

## The flow

1. Branch off `main`: `git switch -c feat/short-codes`
2. Commit, push, open a pull request.
3. Checks must pass and review threads must be resolved.
4. The PR is squash-merged, so `main` gets one commit per PR, titled with the PR title.

Direct pushes and force pushes to `main` are blocked by a repository ruleset.

## PR titles

PR titles follow [Conventional Commits](https://www.conventionalcommits.org/), and CI
rejects ones that don't:

```
<type>(optional scope): <lowercase subject>
```

| Type | Use for |
|---|---|
| `feat` | a new feature (minor version bump) |
| `fix` | a bug fix (patch version bump) |
| `docs` | documentation only |
| `refactor` | code change that is neither a fix nor a feature |
| `perf` | performance improvement |
| `test` | adding or fixing tests |
| `build` | dependencies, packaging |
| `ci` | CI configuration |
| `chore` | anything else that doesn't touch the app |
| `revert` | reverting an earlier commit |

Add `!` after the type for a breaking change: `feat!: drop the v1 API`.

Examples: `feat: add custom short codes`, `fix(redirect): return 404 for expired links`.

## Branch names

`<type>/<short-description>`, for example `fix/expired-link-404`.
