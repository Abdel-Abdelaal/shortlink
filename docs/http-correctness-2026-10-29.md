# HTTP correctness follow-up — 29 October 2026

HEAD previews share redirect encoding and active-link validation with GET,
without incrementing hits. Health and problem responses retain the rendered
GET representation headers while sending no body. This avoids advertising
Content-Length: 0 for a nonempty GET representation (RFC 9110 section 8.6).
Duplicate header fields are preserved when making a bodyless response.
Nonstandard HTTP errors such as 499 and 599 retain their status, details and
custom headers, using a generic title instead of raising ValueError.

## Validation

- 76 repository tests and five schema subtests passed; 100% branch-aware coverage.
- Original six HEAD acceptance checks, five later protocol regressions and four
  applicable HTTP-error holdouts passed (15 total).
- Ruff, strict Pyright, import contracts, dependency and dead-code checks passed.
- Regression tests cover header lengths, duplicate fields, redirect encoding,
  empty HEAD errors, custom error headers and standard/nonstandard status titles.

## Provenance

This is a Codex-assisted corrective follow-up, reusing the retained MiMo run 33
repaired prototype plus the nonstandard-status proposal from PR #54. Codex fixed
the remaining HEAD metadata defect and used bytes(response.body) in error tests
so strict typing accepts both bytes and memoryview responses. No additional
model API call was required. There are no new application dependencies.

The original benchmark patches, scores and draft PR heads remain unchanged.
These corrections are not counted as autonomous MiMo successes. See the
[controller evaluation report](https://github.com/Abdel-Abdelaal/agent-dispatcher/blob/main/docs/quality-results-2026-10-29.md).

Protocol reference: [RFC 9110 section 8.6](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.6).
