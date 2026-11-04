import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import ask_ai

SAMPLE = str(Path(__file__).with_name("sample_plan.json"))


def fake_response(text="Explanation", stop_reason="end_turn"):
    response = MagicMock(stop_reason=stop_reason)
    response.content = [MagicMock(type="text", text=text)]
    return response


def run_cli(*plans, response=None, user="alice"):
    client = MagicMock()
    client.beta.messages.create.return_value = response or fake_response()
    with patch.object(sys, "argv", ["ask_ai.py", *plans]), patch("dotenv.load_dotenv"), patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}), patch("anthropic.Anthropic", return_value=client), patch("getpass.getuser", return_value=user), contextlib.redirect_stdout(io.StringIO()) as output:
        ask_ai.main()
    return client.beta.messages.create, output.getvalue()


class AskAiTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.usage_file = Path(folder.name, "usage.json")
        usage_patch = patch.object(ask_ai, "USAGE_FILE", self.usage_file)
        usage_patch.start()
        self.addCleanup(usage_patch.stop)

    def test_one_plan_sends_report_and_prints_answer(self):
        create, output = run_cli(SAMPLE)
        prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn("Seq Scan on orders", prompt)
        self.assertIn('"Rows Removed by Filter": 990', prompt)
        self.assertNotIn("Plan comparison", prompt)
        self.assertEqual(create.call_args.kwargs["model"], ask_ai.MODEL)
        self.assertIn("Explanation", output)

    def test_two_plans_include_comparison(self):
        create, _ = run_cli(SAMPLE, SAMPLE)
        self.assertIn("Plan comparison", create.call_args.kwargs["messages"][0]["content"])

    def test_refusal_is_reported_as_error_and_counted(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            run_cli(SAMPLE, response=fake_response(stop_reason="refusal"))
        self.assertEqual(ask_ai.usage_today(ask_ai.date.today().isoformat()), {"alice": 1})

    def test_missing_key_has_clear_error(self):
        with patch("dotenv.load_dotenv"), patch.dict("os.environ", clear=True), patch("anthropic.Anthropic") as client, self.assertRaises(ValueError):
            ask_ai.ask("prompt", "alice", "2026-11-04")
        client.assert_not_called()
        self.assertFalse(self.usage_file.exists())

    def test_bad_input_is_rejected_before_calling_api(self):
        for plans in [["missing.json"], [SAMPLE, SAMPLE, SAMPLE]]:
            with self.subTest(plans=plans), patch.object(ask_ai, "ask") as ask, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                with patch.object(sys, "argv", ["ask_ai.py", *plans]):
                    ask_ai.main()
            ask.assert_not_called()

    def test_fourth_request_in_a_day_is_blocked_per_user(self):
        for _ in range(ask_ai.DAILY_LIMIT):
            run_cli(SAMPLE)
        with contextlib.redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit):
            create, _ = run_cli(SAMPLE)
        self.assertIn("Daily limit reached", errors.getvalue())
        # Another user still has their own allowance.
        create, _ = run_cli(SAMPLE, user="bob")
        create.assert_called_once()

    def test_blocked_request_does_not_call_api(self):
        today = ask_ai.date.today().isoformat()
        self.usage_file.write_text(json.dumps({"date": today, "counts": {"alice": ask_ai.DAILY_LIMIT}}))
        client = MagicMock()
        with patch.object(sys, "argv", ["ask_ai.py", SAMPLE]), patch("getpass.getuser", return_value="alice"), patch("anthropic.Anthropic", return_value=client), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            ask_ai.main()
        client.beta.messages.create.assert_not_called()

    def test_counts_reset_on_a_new_day(self):
        self.usage_file.write_text(json.dumps({"date": "2000-01-01", "counts": {"alice": ask_ai.DAILY_LIMIT}}))
        ask_ai.check_limit("alice", "2000-01-02")
        ask_ai.record_use("alice", "2000-01-02")
        self.assertEqual(json.loads(self.usage_file.read_text()), {"date": "2000-01-02", "counts": {"alice": 1}})

    def test_failed_api_call_is_not_counted(self):
        import anthropic
        client = MagicMock()
        client.beta.messages.create.side_effect = anthropic.APIConnectionError(request=MagicMock())
        with patch("dotenv.load_dotenv"), patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}), patch("anthropic.Anthropic", return_value=client), self.assertRaises(ValueError):
            ask_ai.ask("prompt", "alice", "2026-11-04")
        self.assertFalse(self.usage_file.exists())


if __name__ == "__main__":
    unittest.main()
