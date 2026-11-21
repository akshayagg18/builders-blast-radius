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

- Repository: <https://github.com/akshayagg18/builders-blast-radius>
- Submitted commit: `aad38e3e63a5216ba60bf439de38ec8527206db1`
- Receipt: `BB-B53E1F14`
- Scorer version: `blast-radius-1`
- Status: scored and automatically entered in the final as the team's best result
- Practice score: **733.1 s**

| Run | Simulated seconds | CPU seconds | Missed commits |
| ---: | ---: | ---: | ---: |
| 1 | 732.728 | 0.35 | 2 |
| 2 | 732.728 | 0.36 | 2 |
| 3 | 732.728 | 0.36 | 2 |

The scorer reported a 29 ms queue wait and no build, protocol, timeout, memory, or
container failure. The median total is `732.728 + 0.36 = 733.088`, rounded to
733.1 seconds. The two misses account for exactly 600 seconds, so the selector's
zero-penalty official workload cost was 132.728 simulated seconds (133.1 seconds
including median CPU). Builders does not disclose which practice commits were
missed. The live page did not expose a stable rank in the submission receipt.

The official result is 371.410 seconds (33.6%) faster than the all-tests sample
baseline despite the penalties, but it is 579.704 seconds slower than the local
optimized sample result. The difference is evidence that sample-perfect pinned-line
coverage and sentinels did not generalize safely to two unseen practice changes.

## Recommendations after first score

1. Expand structural sentinels before pruning anything. One avoided miss is worth
   300 seconds, while the entire zero-penalty official workload cost only 133.1 seconds.
2. Remove the assumption that comment-only Python patches are harmless. The official
   specification explicitly says they are not promised harmless; route them through
   file- and subsystem-level sentinels.
3. Add broader fallbacks for newly reachable code paths, import-time effects, and
   subprocess-executed optimizer paths that pinned-revision line coverage cannot see.
4. CPU is already negligible at 0.35--0.36 seconds; optimizing map loading cannot
   materially offset even a small increase in miss risk.
5. Preserve the submitted commit and receipt as the first-practice ledger entry before
   experimenting with a more conservative second commit.
