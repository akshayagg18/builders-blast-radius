from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import selector


def load_score_module():
    spec = importlib.util.spec_from_file_location("official_score", ROOT / "experiments" / "score.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PatchParsingTests(unittest.TestCase):
    def test_replacement_anchors_both_old_and_insertion_point(self):
        patch = """diff --git a/sqlglot/a.py b/sqlglot/a.py
--- a/sqlglot/a.py
+++ b/sqlglot/a.py
@@ -10,3 +10,3 @@
 keep
-old
+new
 keep
"""
        [change] = selector.parse_patch(patch)
        self.assertEqual(change.path, "sqlglot/a.py")
        self.assertEqual(change.anchors, {11, 12})
        self.assertEqual(change.changed_text, ["old", "new"])

    def test_python_comment_only_change_is_detected(self):
        patch = """--- a/sqlglot/a.py
+++ b/sqlglot/a.py
@@ -1 +1,2 @@
 value = 1
+# documentation only
"""
        [change] = selector.parse_patch(patch)
        self.assertTrue(change.comment_only)

    def test_deleted_file_keeps_old_path(self):
        patch = """--- a/sqlglot/old.py
+++ /dev/null
@@ -3 +0,0 @@
-dangerous = True
"""
        [change] = selector.parse_patch(patch)
        self.assertEqual(change.path, "sqlglot/old.py")
        self.assertEqual(change.anchors, {3})


class SchedulingTests(unittest.TestCase):
    def test_worker_overhead_can_make_one_worker_optimal(self):
        tests = {
            0: {"number": 0, "seconds": 0.1},
            1: {"number": 1, "seconds": 0.1},
        }
        self.assertEqual(selector.schedule({0, 1}, tests), [[0, 1]])

    def test_long_tests_are_balanced(self):
        tests = {
            number: {"number": number, "seconds": seconds}
            for number, seconds in enumerate((5.0, 4.0, 3.0, 2.0))
        }
        workers = selector.schedule(set(tests), tests)
        self.assertLessEqual(len(workers), selector.MAX_WORKERS)
        self.assertEqual(sorted(number for worker in workers for number in worker), [0, 1, 2, 3])


class SampleRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample = ROOT / "experiments" / "sample"
        cls.tests = json.loads((cls.sample / "tests.json").read_text("utf-8"))["tests"]
        cls.answers = json.loads((cls.sample / "answers.json").read_text("utf-8"))["commits"]
        cls.score = load_score_module()

    def test_optimized_selector_is_valid_and_has_zero_sample_misses(self):
        output = StringIO()
        old_radius = selector.DEFAULT_RADIUS
        try:
            selector.DEFAULT_RADIUS = 3
            with redirect_stdout(output):
                selector.main(self.sample)
        finally:
            selector.DEFAULT_RADIUS = old_radius
        result = self.score.evaluate_run(output.getvalue().encode(), self.tests, self.answers)
        self.assertTrue(result["ok"])
        self.assertEqual(result["missed_commits"], [])
        self.assertLess(result["simulated_milliseconds"], 200_000)


if __name__ == "__main__":
    unittest.main()
