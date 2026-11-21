"""Build the allowed line-coverage and fixture map from pinned sqlglot.

Run after collecting coverage with ``dynamic_context = test_function``.
The output format interns repeated test-number sets to keep the committed map small.
"""

from __future__ import annotations

import ast
import gzip
import json
from pathlib import Path

from coverage import CoverageData


HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE / "sqlglot"
TESTS_JSON = HERE / "sample" / "tests.json"
OUTPUT = HERE.parent / "src" / "coverage_map.json.gz"


def context_name(test_id: str) -> str:
    path, *parts = test_id.split("::")
    module = path.removesuffix(".py").replace("/", ".")
    return ".".join([module, *parts])


def test_function_map(tests: list[dict]) -> dict[str, int]:
    return {context_name(test["id"]): test["number"] for test in tests}


def build_line_map(
    data: CoverageData, context_to_number: dict[str, int]
) -> tuple[list[list[int]], dict[str, dict[str, int]]]:
    sets: list[list[int]] = []
    set_indexes: dict[tuple[int, ...], int] = {}
    files: dict[str, dict[str, int]] = {}

    for measured in sorted(data.measured_files()):
        path = Path(measured)
        try:
            relative = path.relative_to(SOURCE_ROOT).as_posix()
        except ValueError:
            continue
        if not relative.startswith("sqlglot/"):
            continue

        lines: dict[str, int] = {}
        for line, contexts in data.contexts_by_lineno(measured).items():
            numbers = tuple(
                sorted(
                    {
                        context_to_number[context]
                        for context in contexts
                        if context in context_to_number
                    }
                )
            )
            if not numbers:
                continue
            set_index = set_indexes.get(numbers)
            if set_index is None:
                set_index = len(sets)
                set_indexes[numbers] = set_index
                sets.append(list(numbers))
            lines[str(line)] = set_index
        if lines:
            files[relative] = lines

    return sets, files


def function_test_number(
    path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef, id_to_number: dict[str, int]
) -> int | None:
    relative = path.relative_to(SOURCE_ROOT).as_posix()
    module_id = relative.removesuffix(".py")
    parent_class = next(
        (
            parent.name
            for parent in ast.walk(ast.parse(path.read_text("utf-8")))
            if isinstance(parent, ast.ClassDef) and node in parent.body
        ),
        None,
    )
    pieces = [f"{module_id}.py"]
    if parent_class:
        pieces.append(parent_class)
    pieces.append(node.name)
    return id_to_number.get("::".join(pieces))


def build_fixture_map(tests: list[dict]) -> dict[str, list[int]]:
    id_to_number = {test["id"]: test["number"] for test in tests}
    fixture_to_numbers: dict[str, set[int]] = {}

    for path in sorted((SOURCE_ROOT / "tests").rglob("test_*.py")):
        tree = ast.parse(path.read_text("utf-8"))
        class_by_function: dict[ast.AST, str] = {}
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                for child in parent.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        class_by_function[child] = parent.name

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            relative = path.relative_to(SOURCE_ROOT).as_posix()
            test_id = f"{relative}"
            if node in class_by_function:
                test_id += f"::{class_by_function[node]}"
            test_id += f"::{node.name}"
            number = id_to_number.get(test_id)
            if number is None:
                continue

            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                name = ""
                if isinstance(child.func, ast.Name):
                    name = child.func.id
                elif isinstance(child.func, ast.Attribute):
                    name = child.func.attr
                if name not in {"check_file", "load_sql_fixtures", "load_sql_fixture_pairs"}:
                    continue
                if not child.args or not isinstance(child.args[0], ast.Constant):
                    continue
                value = child.args[0].value
                if not isinstance(value, str):
                    continue
                if name == "check_file":
                    fixture = f"tests/fixtures/optimizer/{value}.sql"
                else:
                    fixture = f"tests/fixtures/{value}"
                fixture_to_numbers.setdefault(fixture, set()).add(number)

    return {
        fixture: sorted(numbers) for fixture, numbers in sorted(fixture_to_numbers.items())
    }


def main() -> None:
    tests = json.loads(TESTS_JSON.read_text("utf-8"))["tests"]
    data = CoverageData(basename=str(SOURCE_ROOT / ".coverage"))
    data.read()
    sets, files = build_line_map(data, test_function_map(tests))
    payload = {
        "version": 1,
        "sqlglot_commit": "eb11aec4be8cb2122afe713a4816662c3f0fb2fa",
        "sets": sets,
        "files": files,
        "fixtures": build_fixture_map(tests),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUTPUT, "wt", encoding="utf-8", compresslevel=9) as stream:
        json.dump(payload, stream, separators=(",", ":"), sort_keys=True)
    print(
        f"wrote {OUTPUT}: {len(files)} source files, {len(sets)} unique coverage sets, "
        f"{len(payload['fixtures'])} fixture mappings"
    )


if __name__ == "__main__":
    main()
