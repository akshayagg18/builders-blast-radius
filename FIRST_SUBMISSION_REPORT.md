# First submission report

Prepared: 2026-11-21 SGT

## Submission artifact

- Strategy: pinned-revision changed-line coverage plus fixture ownership, structural
  fallbacks, risk sentinels, and cost-aware LPT scheduling.
- Base image: official pinned `python:3.13-slim` digest.
- Image contents: selector and 344 KB compressed coverage map only.
- Runtime dependencies: Python standard library only.

## Validation

| Check | Result |
| --- | --- |
| Unit tests | 6 passed |
| Pinned SQLGlot coverage collection | 1,620 tests + 25,440 subtests passed; 1 skipped |
| All-tests baseline | 1104.510 s simulated; 0 misses |
| Optimized direct run | 153.396 s simulated; 0 misses |
| Official-limit container run | 153.396 s simulated; 0 misses; exit 0 |
| Container protocol | valid JSONL; all 30 commits; stderr-only diagnostics |

The optimized selector reduces sample simulated time by 951.114 seconds (86.1%).

## Official result

Pending repository publication and first practice submission. This section will be
updated with the exact repository, commit, score, simulated seconds, CPU seconds,
missed-commit count, rank, and scorer feedback.

## Recommendations after first score

1. Treat a score near the zero-miss sample projection as evidence the coverage map
   generalizes; then reduce over-selection in generic dialect and typing changes.
2. If the server reports one or more misses, expand sentinels before pruning anything.
   One avoided miss is worth up to 300 seconds.
3. Use CPU feedback to confirm gzip/JSON loading is negligible. If not, replace the
   runtime payload with a compact binary array encoded using only the standard library.
4. Preserve this exact commit as the conservative final candidate before experimenting.
