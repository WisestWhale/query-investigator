import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal

import explain_query
from plan_report import PlanReport


class PlanReportTests(unittest.TestCase):
    def test_nested_plan_lists_children_and_measured_rows(self):
        data = json.loads(Path(__file__).with_name("sample_plan.json").read_text())
        output = PlanReport(data).to_text()
        self.assertIn("Sort", output)
        self.assertIn("  - Seq Scan on orders", output)
        self.assertIn("actual rows per loop: 10; loops: 1", output)
        self.assertIn("Execution time: 0.8 ms", output)
        self.assertIn("Rows removed by filter per loop: 990", output)

    def test_estimated_plan_does_not_invent_measurements(self):
        output = PlanReport({"Plan": {"Node Type": "Index Scan", "Index Name": "orders_total_idx", "Plan Rows": 2}}).to_text()
        self.assertIn("Estimates only", output)
        self.assertIn("Index: orders_total_idx", output)
        self.assertNotIn("actual rows", output)

    def test_invalid_plan_has_clear_error(self):
        for data in [[], {}, {"Plan": {}}, {"Plan": {"Node Type": "Sort", "Plans": [None]}}]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                PlanReport(data)

    def test_demo_does_not_connect(self):
        with patch.object(sys, "argv", ["explain_query.py", "--demo"]), patch.object(explain_query, "explain") as query, contextlib.redirect_stdout(io.StringIO()) as output:
            explain_query.main()
        query.assert_not_called()
        self.assertIn("Sample data", output.getvalue())
        self.assertIn("Seq Scan on orders", output.getvalue())

    def test_non_finite_total_is_rejected_before_connecting(self):
        for value in ["nan", "Infinity", "not-a-number"]:
            with patch.object(sys, "argv", ["explain_query.py", "--total", value]), patch.object(explain_query, "explain") as query, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                explain_query.main()
            self.assertEqual(error.exception.code, 2)
            query.assert_not_called()

    def test_database_query_is_parameterized_read_only_and_bounded(self):
        connection = MagicMock()
        cursor = connection.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ([{"Plan": {"Node Type": "Seq Scan"}}],)
        with patch("dotenv.load_dotenv"), patch.dict("os.environ", {"DATABASE_URL": "test-database"}), patch("psycopg.connect", return_value=connection):
            explain_query.explain(Decimal("40.5"), analyze=True)
        statements = [call.args for call in cursor.execute.call_args_list]
        self.assertEqual(statements[0], ("SET TRANSACTION READ ONLY",))
        self.assertEqual(statements[1], ("SET LOCAL statement_timeout = '10s'",))
        self.assertEqual(statements[2], ("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT * FROM orders WHERE total = %s", (Decimal("40.5"),)))


if __name__ == "__main__":
    unittest.main()
