# Blast Radius research and scoring analysis

Research snapshot: 2026-11-21 09:30--14:38 SGT (2026-11-20 20:30--
2026-11-21 01:38 ET).

## Official hackathon rules

Sources: [Buildathon guide and rules](https://www.joinbuilders.org/buildathon),
[leaderboard](https://www.joinbuilders.org/buildathon/leaderboard),
[Blast Radius track](https://www.joinbuilders.org/buildathon/tracks/blast-radius), and
[exact scoring contract](https://www.joinbuilders.org/buildathon/tracks/blast-radius/files/SCORING.md).

- Eligibility is limited to current students at any school worldwide, registered
  with a school email. Teams may have one or two people, and a person may be on one
  team. Remote participation is allowed.
- AI and other tools are allowed unless a track says otherwise. Blast Radius allows
  any language, libraries, and AI.
- Work must be MIT licensed. Pre-existing and open-source code is permitted when
  named in the README.
- The event opened Friday, November 20, 2026 at 6:00 PM ET. Submissions close
  Sunday, November 22 at 11:00 AM ET; the closing ceremony begins at noon ET.
- The track accepts a public GitHub repository with a root Dockerfile and an exact
  commit. The initial limit is one submission per hour. Waiting and rejected jobs
  count against the limit; only one entry per team may be active at a time.
- Practice scores update the live board and preserve the best score, but carry no
  prize. The final uses the chosen commit, or the best practice commit if none is
  chosen, on unseen changes. At least the top five are rerun five times each, one at
  a time on an idle machine; the median replaces the provisional result.
- Equal practice scores rank the earlier submission first. In the final, entries
  within one second of the best are treated as tied and ordered by submission time.
- The winner of each track receives $5,000; second place receives nothing.
- Team code may not be shared. Duplicate repository/commit/archive submissions are
  disqualified, with the later entry losing. Top entries may be inspected and teams
  may be asked to explain them.

### Live status and community scan

- The signed-in track page grew from 61 teams during the initial scan to 176 teams
  at first submission. At 14:38 SGT, the leading visible practice scores were
  fortnite pirate token 142.9 s, ND 146.3 s, 67 151.8 s, and SophiaOmri 153.7 s.
  The official baseline remained 1614.1 s.
- The only visible organizer announcement was the kickoff greeting, “May the odds
  be ever in your favor”; no scoring-rule change was visible.
- Focused public GitHub searches for the event name, scorer metric, and sample-kit
  name did not surface a relevant competitor repository. Unrelated projects named
  “Blast Radius” were excluded, and competitor code would not be used under the
  track's no-sharing rule.

## Exact input/output and rejection contract

The downloaded official kit is preserved under `experiments/`; its `score.py` was
read in full and used for every benchmark.

- `/data/tests.json` is `{"tests":[...]}`. Every test has a contiguous integer
  `number`, pytest `id`, source `file`, and duration in seconds. `skipped` tests have
  no number and cannot fail.
- `/data/commits/<id>.patch` contains one independent unified diff against SQLGlot
  commit `eb11aec4be8cb2122afe713a4816662c3f0fb2fa`.
- stdout must contain exactly one line per commit:
  `{"commit":"k7q2","workers":[[12,845],[3,77]]}`. `workers:[]` runs nothing.
- Logs belong on stderr. Invalid UTF-8, non-JSON, extra/missing keys, unknown or
  repeated commits, unknown or repeated test numbers, wrong types, more than eight
  non-empty workers, missing commits, and stdout over 2 MB reject a run.
- JSON floats such as `3.0` are accepted as whole test numbers; booleans, strings,
  and non-integral floats are not. Empty workers are discarded before counting.

## Scoring arithmetic

Durations are converted to integer milliseconds by half-up rounding. For commit
`c`, selected tests are partitioned into workers `W(c)`:

```text
load(w)       = sum(duration_ms(test) for test in w)
commit_cost   = 0                                      if W(c) is empty
              = max(load(w)) + 2000 * |W(c)|           otherwise
simulated     = sum(commit_cost) + 300000 * missed_commits
total         = simulated + aggregate container CPU microseconds
submission    = median of 3 valid totals, rounded half-up to 0.1 second
```

A commit is missed if **any** failing test is omitted; the penalty is once per
commit, not once per test. Build CPU is free. Runtime CPU for the selector and all
children is charged.

### Expected-value threshold

Suppose skipping tests saves `S` seconds of makespan/worker overhead and creates
probability `q` of turning the commit into a miss. The expected score change is:

```text
E[change] = -S + 300q
```

Skipping is favorable only when `q < S/300`. Saving one second requires confidence
above 99.667% that the skipped tests are unnecessary. Saving 30 seconds tolerates at
most a 10% miss probability. This strongly favors conservative, evidence-backed
selection. Worker startup is discontinuous, so a 1.9-second test may be cheaper to
keep on an existing worker than to activate another worker for a nominally better
balance.

## Runtime and build environment

- Repository limit: 20 MB. Submodules and Git LFS are not fetched.
- Build: network access, 4 CPU cores, 8 GB RAM, 10 minutes. Downloads are restricted
  to public package registries, fixed GitHub releases, and the pinned SQLGlot repo.
- Run: no network, 2 CPU cores, 4 GB RAM, 3 minutes for practice and 4.5 minutes for
  the approximately 1.5x larger final batch.
- Runtime user is `nobody`; `HOME=/tmp`; root filesystem is read-only; `/tmp` is an
  empty 64 MB tmpfs; maximum 256 processes.
- Each image runs three times and all runs must be valid.

## SQLGlot structure and dependency findings

SQLGlot describes itself as a no-dependency Python SQL parser, transpiler, optimizer,
and execution engine supporting more than 30 dialects and backed by a comprehensive
test suite ([official repository](https://github.com/tobymao/sqlglot)). At the pinned
revision, the numbered suite contains 1,620 tests across 58 files, totaling 103.047
recorded seconds.

The suite is highly skewed:

| Test file | Tests | Recorded seconds |
| --- | ---: | ---: |
| `tests/test_executor.py` | 60 | 31.565 |
| `tests/test_parser.py` | 81 | 29.143 |
| `tests/test_optimizer.py` | 167 | 19.818 |
| `tests/test_generator.py` | 10 | 6.752 |
| all other files | 1,302 | 15.769 |

Two executor tests alone cost 21.454 s and 3.863 s. Selection quality on these tests
dominates makespan.

Important dependency patterns:

- Dialect behavior is spread across `sqlglot/dialects`, `parsers`, `generators`, and
  dialect-specific tests. Dialect constants can also affect optimizer fixtures.
- Optimizer tests load SQL/expected-output pairs from
  `tests/fixtures/optimizer/*.sql`.
- [`TestOptimizer` uses a `ProcessPoolExecutor`](https://raw.githubusercontent.com/tobymao/sqlglot/eb11aec4be8cb2122afe713a4816662c3f0fb2fa/tests/test_optimizer.py),
  so parent-process dynamic contexts miss some child-executed dependencies.
- SQLGlot's serializer is part of that multiprocessing boundary. A one-line boolean
  mutation in `serde.py` affected dialect, executor, expression, optimizer, and serde
  tests in the sample.
- Fixture ownership is unusually precise: a modified optimizer fixture usually maps
  to one named optimizer test, giving a high-confidence low-cost selection.

## Test-impact research

Rothermel and Harrold's [safe regression test selection](https://www.cs.purdue.edu/homes/xyzhang/spring07/Papers/p173-rothermel.pdf)
selects tests that execute changed code and defines safety as retaining every test
capable of exposing a fault, while accepting that extra tests may remain. Ekstazi's
[dynamic file dependency technique](https://users.ece.utexas.edu/~gligoric/papers/GligoricETAL15Ekstazi.pdf)
shows a pragmatic coarser-grained alternative and reported 32% average end-to-end
reduction, 54% on longer suites. Facebook's
[Predictive Test Selection](https://arxiv.org/abs/1810.05286) halved infrastructure
cost while reporting more than 99.9% of faulty changes, but it depends on historical
outcome data unavailable here.

Coverage.py supports dynamic `test_function` contexts explicitly to answer “what
test ran this line?” ([documentation](https://coverage.readthedocs.io/en/7.11.0/contexts.html)).
Pytest test IDs select exact module/class/method nodes using `::`
([documentation](https://docs.pytest.org/en/stable/how-to/usage.html)). These features
make a pinned-revision line-to-test map both legitimate under the rules and compact.

For scheduling, Longest Processing Time first places descending-duration jobs on the
currently lightest worker. Graham's original identical-processor analysis is the
foundation ([SIAM DOI 10.1137/0117039](https://epubs.siam.org/doi/abs/10.1137/0117039)).
The challenge adds a fixed worker charge, so this submission evaluates LPT for every
worker count from 1 through 8 instead of always maximizing parallelism.

## Sample observations and hypotheses

The 30 sample commits contain 12 harmless changes and 18 failing changes. Failure
cardinality is heavy-tailed: 13 fail one test, while one serializer mutation fails 37.
This makes file-name-only selection insufficient but validates a hybrid:

1. exact/nearby changed-line dynamic coverage;
2. direct fixture ownership;
3. source/test naming conventions;
4. small, risk-triggered sentinel portfolios for subprocess and cross-layer gaps;
5. zero-test output only for high-confidence comment-only changes.

The coverage run on the pinned revision passed 1,620 tests and 25,440 subtests. The
interned map covers 170 source files with 6,954 distinct test sets and compresses to
344,378 bytes. Radius experiments all retained zero sample misses:

| Line radius | Simulated seconds |
| ---: | ---: |
| 0 | 153.364 |
| 1 | 153.396 |
| 3 (chosen) | 153.396 |
| 4 | 154.471 |
| 8 | 159.811 |
| 12 | 165.255 |

Radius 3 is retained for unseen multiline edits at negligible sample cost. The main
remaining risk is behavior newly reachable only after an edit: old-version coverage
cannot observe a path that did not previously execute. Structural sentinels and the
nearest-executable-line fallback mitigate but cannot prove safety.

## First official practice result

Builders accepted public commit
`aad38e3e63a5216ba60bf439de38ec8527206db1` under receipt `BB-B53E1F14`.
All three runs completed and reported the same 732.728 simulated seconds with two
missed commits; CPU was 0.35, 0.36, and 0.36 seconds. The scored median was 733.1
seconds and was automatically entered in the final as the team's current best.

Subtracting the two 300-second penalties gives a 132.728-second zero-penalty
workload cost. Thus, the selector was highly efficient on the tests it chose, but
coverage safety dominated the score. The official page never reveals which commits
were missed. The most actionable model correction is to stop treating comment-only
Python changes as guaranteed harmless and to broaden structural fallbacks for
newly reachable, import-time, and subprocess behavior before any further pruning.
