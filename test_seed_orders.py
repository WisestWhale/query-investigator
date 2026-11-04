import contextlib
import io
import sys
import unittest
from unittest.mock import patch, MagicMock

import seed_orders


def run_seed(table_exists, reset):
    connection = MagicMock()
    cursor = connection.__enter__.return_value.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (table_exists,)
    with patch("dotenv.load_dotenv"), patch.dict("os.environ", {"DATABASE_URL": "test-database"}), patch("psycopg.connect", return_value=connection):
        seed_orders.seed(1000, reset)
    return [call.args for call in cursor.execute.call_args_list]


class SeedOrdersTests(unittest.TestCase):
    def test_new_table_is_created_filled_and_analyzed(self):
        statements = run_seed(table_exists=False, reset=False)
        self.assertEqual(statements[1], (seed_orders.CREATE_TABLE,))
        self.assertIn((seed_orders.INSERT_ROWS, (1000,)), statements)
        self.assertEqual(statements[-1], ("ANALYZE orders",))
        self.assertNotIn(("DROP TABLE orders",), statements)

    def test_existing_table_is_kept_without_reset(self):
        with self.assertRaises(ValueError):
            run_seed(table_exists=True, reset=False)

    def test_reset_drops_existing_table(self):
        statements = run_seed(table_exists=True, reset=True)
        self.assertEqual(statements[1], ("DROP TABLE orders",))
        self.assertEqual(statements[2], (seed_orders.CREATE_TABLE,))

    def test_row_count_must_be_positive(self):
        with patch.object(sys, "argv", ["seed_orders.py", "--rows", "0"]), patch.object(seed_orders, "seed") as seed, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            seed_orders.main()
        seed.assert_not_called()


if __name__ == "__main__":
    unittest.main()
