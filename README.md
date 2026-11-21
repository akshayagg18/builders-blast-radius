# Blast Radius: coverage-guided CI test selection

Submission for the RWX **Blast Radius** track at Builders Buildathon 2026.

The program receives independent patches against SQLGlot commit
`eb11aec4be8cb2122afe713a4816662c3f0fb2fa`, selects tests likely to expose each
patch, and schedules them over up to eight workers. It emits exactly one JSON line
per commit.

## Result

| Selector | Sample simulated time | Missed commits |
| --- | ---: | ---: |
| All tests, cost-optimal worker count | 1104.510 s | 0 |
| Coverage-guided optimized selector | **153.396 s** | **0** |

The optimized sample result is an 86.1% reduction from the local all-tests baseline.
Selector CPU time is under 0.5 seconds per 30-commit sample batch on the local
linux/amd64 container; the official server measures CPU independently.

## Strategy

The solution uses a 344 KB map generated once from the pinned SQLGlot revision:

1. Coverage.py dynamic contexts record which test function executed each source line.
2. The build script interns identical test sets and compresses the line map.
3. At runtime, a strict unified-diff parser locates changed old-source lines.
4. Tests covering a three-line neighborhood are selected.
5. Fixture changes map directly to the test method that owns the fixture.
6. Naming-based ownership and small component-specific sentinel portfolios protect
   against subprocess coverage gaps and high-risk boolean mutations.
7. Pure Python comment-only changes run nothing.
8. For every selected set, Longest Processing Time first scheduling is evaluated
   with 1 through 8 workers; the worker count minimizing
   `makespan + 2 seconds * workers` is emitted.

No sample patch, answer, commit id, or edit-kind lookup is used by the runtime
selector. The committed map is built only from the allowed pinned revision.

## Repository layout

```text
Dockerfile                         submission image
src/selector.py                    optimized runtime selector
src/baseline.py                    preserved all-tests baseline
src/coverage_map.json.gz           permitted pinned-revision coverage map
tests/test_selector.py             parser, scheduler, and sample regressions
experiments/build_coverage_map.py   reproducible map builder
experiments/score.py                official local scorer
experiments/sample/                 official 30-commit sample
research.md                         rules, scoring, research, hypotheses
FIRST_SUBMISSION_REPORT.md          submission result and next steps
submission/SUBMISSION.md            operational submission notes
```

## Run locally

Requirements: Docker and Python 3.9 or newer. GNU Make is optional.

```bash
make test
make baseline
make sample
```

Equivalent Windows commands:

```powershell
py -3 -m unittest discover -s tests -v
docker build --platform linux/amd64 -t blast-radius-entry .
```

The `Makefile` runs the image with the official resource, filesystem, user, and
network restrictions and scores `experiments/output.jsonl` with the official scorer.

## Rebuild the coverage map

The checked-in map is already submission-ready. Rebuilding it is an offline
development task, not part of the Docker build:

```powershell
git clone https://github.com/tobymao/sqlglot.git experiments/sqlglot
git -C experiments/sqlglot checkout eb11aec4be8cb2122afe713a4816662c3f0fb2fa
py -3 -m venv experiments/.venv
experiments/.venv/Scripts/python -m pip install -r experiments/requirements.lock coverage==7.11.0
```

Run SQLGlot's suite under Coverage.py with `dynamic_context = test_function`, then:

```powershell
experiments/.venv/Scripts/python experiments/build_coverage_map.py
```

The full pinned suite used to produce the map passed: 1,620 tests and 25,440
subtests, with one skipped test.

## Safety and protocol

- stdout contains only compact JSON answer lines; diagnostics go to stderr.
- Every patch file gets exactly one answer.
- Tests are de-duplicated before scheduling.
- Empty selections emit `"workers":[]`.
- Worker count never exceeds eight.
- Only test numbers present in `/data/tests.json` are emitted.
- The image runs as UID/GID 65534 and needs no writes or network.

## License

MIT. SQLGlot and the official sample kit retain their respective upstream terms.
