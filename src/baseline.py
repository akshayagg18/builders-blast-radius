"""Conservative zero-miss baseline: run every test on every commit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


DATA = Path("/data")
MAX_WORKERS = 8
WORKER_COST_MS = 2_000


def lpt(tests: list[dict], worker_count: int) -> tuple[list[list[int]], list[int]]:
    workers = [[] for _ in range(worker_count)]
    loads = [0] * worker_count
    for test in sorted(tests, key=lambda item: (-round(item["seconds"] * 1000), item["number"])):
        target = min(range(worker_count), key=lambda index: (loads[index], index))
        workers[target].append(test["number"])
        loads[target] += round(test["seconds"] * 1000)
    return workers, loads


def schedule(tests: list[dict]) -> list[list[int]]:
    if not tests:
        return []
    best: tuple[int, list[list[int]]] | None = None
    for count in range(1, min(MAX_WORKERS, len(tests)) + 1):
        workers, loads = lpt(tests, count)
        candidate = (max(loads) + WORKER_COST_MS * count, workers)
        if best is None or candidate[0] < best[0]:
            best = candidate
    assert best is not None
    return best[1]


def main(data: Path = DATA) -> None:
    tests = json.loads((data / "tests.json").read_text("utf-8"))["tests"]
    workers = schedule(tests)
    for patch in sorted((data / "commits").glob("*.patch")):
        print(json.dumps({"commit": patch.stem, "workers": workers}, separators=(",", ":")))
    print(f"baseline selected all {len(tests)} tests", file=sys.stderr)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DATA)
