import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from compare_plans import compare_reports, main
from plan_report import PlanReport


def report(time=None, node="Seq Scan"):
    data = {"Plan": {"Node Type": node, "Relation Name": "orders"}}
    if time is not None:
        data["Execution Time"] = time
    return PlanReport(data)


class ComparePlanTests(unittest.TestCase):
    def test_timing_difference_and_step_change(self):
        text = compare_reports(report(20), report(5, "Index Scan"))
        self.assertIn("Time change: -15.000 ms", text)
        self.assertIn("Percentage change: -75.0%", text)
        self.assertIn("Seq Scan on orders: 1 -> 0", text)
        self.assertIn("Index Scan on orders: 0 -> 1", text)
        self.assertIn("Time change: +15.000 ms", compare_reports(report(5), report(20)))

    def test_estimates_do_not_become_measured_times(self):
        text = compare_reports(report(), report(5))
        self.assertIn("Timing comparison unavailable", text)
        self.assertNotIn("Percentage change", text)

    def test_zero_baseline_has_no_percentage(self):
        text = compare_reports(report(0), report(1))
        self.assertIn("Time change: +1.000 ms", text)
        self.assertIn("before time is zero", text)

    def test_invalid_timings_are_rejected(self):
        for time in [-1, float("nan"), float("inf"), True, "5"]:
            with self.subTest(time=time), self.assertRaises(ValueError):
                compare_reports(report(time), report(2))

    def test_nested_repeated_steps_are_counted(self):
        before = PlanReport({"Plan": {"Node Type": "Nested Loop", "Plans": [
            {"Node Type": "Seq Scan", "Relation Name": "orders"},
            {"Node Type": "Seq Scan", "Relation Name": "orders"},
        ]}})
        after = PlanReport({"Plan": {"Node Type": "Nested Loop", "Plans": [
            {"Node Type": "Index Scan", "Relation Name": "orders", "Index Name": "orders_total_idx"},
        ]}})
        text = compare_reports(before, after)
        self.assertIn("Seq Scan on orders: 2 -> 0", text)
        self.assertIn("Index Scan on orders using orders_total_idx: 0 -> 1", text)

    def test_cli_compares_sample_without_database(self):
        path = str(Path(__file__).with_name("sample_plan.json"))
        with patch.object(sys, "argv", ["compare_plans.py", path, path]), contextlib.redirect_stdout(io.StringIO()) as output:
            main()
        self.assertIn("Time change: +0.000 ms", output.getvalue())
        self.assertIn("Step counts unchanged", output.getvalue())


if __name__ == "__main__":
    unittest.main()
