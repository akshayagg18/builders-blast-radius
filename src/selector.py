"""Cost-aware coverage-guided test selection for RWX Blast Radius."""

from __future__ import annotations

import gzip
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


DATA = Path("/data")
HERE = Path(__file__).resolve().parent
MAP_PATH = HERE / "coverage_map.json.gz"
MAX_WORKERS = 8
WORKER_COST_MS = 2_000
DEFAULT_RADIUS = 3
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass
class FileChange:
    path: str
    anchors: set[int] = field(default_factory=set)
    changed_text: list[str] = field(default_factory=list)

    @property
    def comment_only(self) -> bool:
        meaningful = [line.strip() for line in self.changed_text if line.strip()]
        return bool(meaningful) and all(line.startswith("#") for line in meaningful)

    @property
    def high_risk_logic_change(self) -> bool:
        """Recognize small mutations that can invert or broaden control flow."""
        joined = "\n".join(self.changed_text)
        return (
            (" and " in joined and " or " in joined)
            or ("if not " in joined and re.search(r"\bif (?!not\b)", joined) is not None)
            or any(token in joined for token in (" != ", " <= ", " >= "))
        )


def parse_patch(text: str) -> list[FileChange]:
    """Return old-file line anchors for every changed file in a unified diff."""
    changes: list[FileChange] = []
    current: FileChange | None = None
    old_line: int | None = None
    old_path: str | None = None

    for line in text.splitlines():
        if line.startswith("--- "):
            raw = line[4:].strip()
            old_path = raw[2:] if raw.startswith("a/") else raw
            continue
        if line.startswith("+++ "):
            raw = line[4:].strip()
            if raw == "/dev/null":
                path = old_path
            else:
                path = raw[2:] if raw.startswith("b/") else raw
            if path and path != "/dev/null":
                current = FileChange(path=path)
                changes.append(current)
            else:
                current = None
            old_line = None
            continue

        match = HUNK_RE.match(line)
        if match and current is not None:
            old_line = int(match.group(1))
            continue
        if current is None or old_line is None or not line:
            continue

        marker, body = line[0], line[1:]
        if marker == " ":
            old_line += 1
        elif marker == "-":
            current.anchors.add(old_line)
            current.changed_text.append(body)
            old_line += 1
        elif marker == "+":
            current.anchors.update((max(1, old_line - 1), old_line))
            current.changed_text.append(body)
        elif marker == "\\":
            continue

    return changes


def load_map() -> dict:
    with gzip.open(MAP_PATH, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def line_coverage(change: FileChange, coverage: dict, radius: int) -> set[int]:
    line_map = coverage["files"].get(change.path)
    if not line_map:
        return set()
    selected: set[int] = set()
    sets = coverage["sets"]
    for anchor in change.anchors:
        for line in range(max(1, anchor - radius), anchor + radius + 1):
            index = line_map.get(str(line))
            if index is not None:
                selected.update(sets[index])
    if selected:
        return selected

    # An uncovered added/deleted line is still risky. Use the nearest executable
    # line in the same file rather than silently selecting nothing.
    numbered_lines = [int(line) for line in line_map]
    for anchor in change.anchors:
        nearest = min(numbered_lines, key=lambda line: abs(line - anchor))
        selected.update(sets[line_map[str(nearest)]])
    return selected


def fixture_tests(change: FileChange, coverage: dict) -> set[int]:
    direct = coverage["fixtures"].get(change.path)
    return set(direct or ())


def same_file_tests(path: str, tests: list[dict]) -> set[int]:
    return {test["number"] for test in tests if test["file"] == path}


def structural_fallback(change: FileChange, tests: list[dict]) -> set[int]:
    path = change.path
    selected: set[int] = set()
    name = Path(path).stem

    if path.startswith("tests/"):
        return same_file_tests(path, tests)
    if path.startswith(("sqlglot/dialects/", "sqlglot/parsers/", "sqlglot/generators/")):
        selected.update(same_file_tests(f"tests/dialects/test_{name}.py", tests))
    if path.startswith("sqlglot/optimizer/"):
        needle = name.removesuffix("s")
        selected.update(
            test["number"]
            for test in tests
            if test["file"] in {"tests/test_optimizer.py", "tests/test_optimize_cross_joins.py"}
            and needle in test["id"]
        )
    if path.startswith("sqlglot/"):
        selected.update(same_file_tests(f"tests/test_{name}.py", tests))
    return selected


def named_tests(tests: list[dict], names: set[str]) -> set[int]:
    return {
        test["number"]
        for test in tests
        if test["id"].rsplit("::", 1)[-1] in names
    }


def risk_portfolio(change: FileChange, tests: list[dict], coverage: dict) -> set[int]:
    """Cheap sentinels for dependencies missed by line coverage and subprocesses."""
    path = change.path
    selected: set[int] = set()

    if path.startswith("sqlglot/optimizer/") and change.high_risk_logic_change:
        module_test = f"test_{Path(path).stem}"
        selected.update(
            named_tests(
                tests,
                {
                    module_test,
                    "test_optimize",
                    "test_optimize_special_joins",
                    "test_tpcds",
                    "test_tpch",
                    "test_execute_tpcds",
                    "test_execute_tpch",
                },
            )
        )

    if path == "sqlglot/serde.py" and change.high_risk_logic_change:
        for numbers in coverage["fixtures"].values():
            selected.update(numbers)
        selected.update(same_file_tests("tests/test_serde.py", tests))

    if path.startswith("sqlglot/typing/") and change.high_risk_logic_change:
        selected.update(
            named_tests(
                tests,
                {
                    "test_annotate_funcs",
                    "test_annotate_types",
                    "test_optimize",
                    "test_qualify_columns",
                    "test_simplify",
                },
            )
        )

    if path.startswith(("sqlglot/dialects/", "sqlglot/parsers/", "sqlglot/generators/")):
        selected.update(
            named_tests(
                tests,
                {
                    "test_annotate_types",
                    "test_optimize",
                    "test_qualify_columns",
                    "test_qualify_tables",
                    "test_quote_identifiers",
                    "test_simplify",
                },
            )
        )
    return selected


def select_tests(
    patch_text: str, tests: list[dict], coverage: dict, radius: int = DEFAULT_RADIUS
) -> set[int]:
    selected: set[int] = set()
    for change in parse_patch(patch_text):
        # Pure Python comments do not alter runtime behavior. Treating them as
        # zero-risk saves worker startup cost on harmless commits.
        if change.comment_only and change.path.endswith(".py"):
            continue
        direct_fixture = fixture_tests(change, coverage)
        if direct_fixture:
            selected.update(direct_fixture)
            continue
        impacted = line_coverage(change, coverage, radius)
        selected.update(impacted)
        # Convention-based ownership is inexpensive and protects against test
        # execution in subprocesses, which ordinary dynamic contexts can miss.
        selected.update(structural_fallback(change, tests))
        selected.update(risk_portfolio(change, tests, coverage))
    return selected


def lpt(tests: list[dict], worker_count: int) -> tuple[list[list[int]], list[int]]:
    workers = [[] for _ in range(worker_count)]
    loads = [0] * worker_count
    for test in sorted(tests, key=lambda item: (-round(item["seconds"] * 1000), item["number"])):
        target = min(range(worker_count), key=lambda index: (loads[index], index))
        workers[target].append(test["number"])
        loads[target] += round(test["seconds"] * 1000)
    return workers, loads


def schedule(selected: set[int], tests_by_number: dict[int, dict]) -> list[list[int]]:
    tests = [tests_by_number[number] for number in selected if number in tests_by_number]
    if not tests:
        return []
    best_cost: int | None = None
    best_workers: list[list[int]] = []
    for count in range(1, min(MAX_WORKERS, len(tests)) + 1):
        workers, loads = lpt(tests, count)
        cost = max(loads) + WORKER_COST_MS * count
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best_workers = workers
    return best_workers


def main(data: Path = DATA) -> None:
    started = time.process_time()
    payload = json.loads((data / "tests.json").read_text("utf-8"))
    tests = payload["tests"]
    tests_by_number = {test["number"]: test for test in tests}
    coverage = load_map()
    radius = int(os.environ.get("BLAST_RADIUS_NEIGHBORHOOD", DEFAULT_RADIUS))

    total_selected = 0
    for patch in sorted((data / "commits").glob("*.patch")):
        selected = select_tests(patch.read_text("utf-8"), tests, coverage, radius)
        total_selected += len(selected)
        workers = schedule(selected, tests_by_number)
        print(json.dumps({"commit": patch.stem, "workers": workers}, separators=(",", ":")))
    print(
        f"coverage selector answered all commits; selected {total_selected} test instances; "
        f"selector CPU {time.process_time() - started:.6f}s",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DATA)
