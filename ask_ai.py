import argparse
from datetime import date
import getpass
import json
import os
from pathlib import Path

from compare_plans import compare_reports
from plan_report import PlanReport

MODEL = "claude-opus-5-5"
DAILY_LIMIT = 3
# Counts requests per user for the current day only; older days are discarded.
USAGE_FILE = Path(__file__).with_name(".ask_ai_usage.json")

SYSTEM = """You explain PostgreSQL query plans to someone learning databases.
Use only the evidence you are given. Explain what each step does and why the
planner might have chosen it. When two plans are given, explain what changed and
whether the evidence supports an improvement. Say clearly when the evidence is
missing or too thin to conclude something, for example a single run or estimates
without measurements. Do not invent numbers. Keep it short and use plain language."""


def build_prompt(reports):
    parts = []
    for name, report in reports:
        parts.append(f"## Plan: {name}\n{report.to_text()}\n\nRaw EXPLAIN JSON:\n{json.dumps(report.data, indent=2)}")
    if len(reports) == 2:
        parts.append(compare_reports(reports[0][1], reports[1][1]))
    return "\n\n".join(parts)


def usage_today(today):
    try:
        usage = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(usage, dict) or usage.get("date") != today or not isinstance(usage.get("counts"), dict):
        return {}
    return usage["counts"]


def check_limit(user, today):
    if usage_today(today).get(user, 0) >= DAILY_LIMIT:
        raise ValueError(f"Daily limit reached: {DAILY_LIMIT} AI requests per user. Try again tomorrow.")


def record_use(user, today):
    counts = usage_today(today)
    counts[user] = counts.get(user, 0) + 1
    USAGE_FILE.write_text(json.dumps({"date": today, "counts": counts}, indent=2) + "\n", encoding="utf-8")


def ask(prompt, user, today):
    import anthropic
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("Set ANTHROPIC_API_KEY in .env before asking Claude.")
    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            output_config={"effort": "medium"},
            # If the model declines, the API retries on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.AuthenticationError:
        raise ValueError("Claude API key missing or invalid. Set ANTHROPIC_API_KEY in .env.") from None
    except anthropic.APIError as error:
        raise ValueError(f"Claude API request failed: {error}") from None
    # Count every answered request, refusals included, because each one is billed.
    record_use(user, today)
    if response.stop_reason == "refusal":
        raise ValueError("Claude declined to answer this request.")
    return "\n".join(block.text for block in response.content if block.type == "text")


def main():
    parser = argparse.ArgumentParser(description="Ask Claude to explain one saved plan, or what changed between two.")
    parser.add_argument("plans", type=Path, nargs="+", help="One or two saved EXPLAIN JSON files.")
    args = parser.parse_args()
    if len(args.plans) > 2:
        parser.error("Give one plan to explain, or two to compare.")
    try:
        reports = [(path.name, PlanReport(json.loads(path.read_text(encoding="utf-8-sig")))) for path in args.plans]
        user, today = getpass.getuser(), date.today().isoformat()
        check_limit(user, today)
        print(ask(build_prompt(reports), user, today))
        print(f"\nAI explanation by {MODEL}. Check it against explain_query.py --load before relying on it.")
    except (OSError, ValueError, RecursionError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
