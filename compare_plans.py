import argparse
from collections import Counter
import json
import math
from pathlib import Path

from plan_report import PlanReport


def execution_time(report):
    value = report.data.get("Execution Time")
    if value is None:
        return None
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0):
        raise ValueError("Execution Time must be a finite, nonnegative number.")
    return value


def step_counts(report):
    counts = Counter()
    for _, node in report.steps():
        label = node["Node Type"]
        if node.get("Relation Name"):
            label += f" on {node['Relation Name']}"
        if node.get("Index Name"):
            label += f" using {node['Index Name']}"
        counts[label] += 1
    return counts


def compare_reports(before, after):
    old_time, new_time = execution_time(before), execution_time(after)
    lines = ["Plan comparison"]
    if old_time is not None and new_time is not None:
        change = new_time - old_time
        lines.append(f"Execution time: {old_time:.3f} ms -> {new_time:.3f} ms")
        lines.append(f"Time change: {change:+.3f} ms (negative means less time)")
        if old_time > 0:
            lines.append(f"Percentage change: {change / old_time * 100:+.1f}%")
        else:
            lines.append("Percentage change: unavailable because the before time is zero.")
    else:
        lines.append("Timing comparison unavailable: both plans need measured Execution Time.")
    old_steps, new_steps = step_counts(before), step_counts(after)
    changes = [
        f"- {label}: {old_steps[label]} -> {new_steps[label]}"
        for label in sorted(old_steps.keys() | new_steps.keys())
        if old_steps[label] != new_steps[label]
    ]
    if changes:
        lines += ["Changed step counts:"] + changes
    else:
        lines.append("Step counts unchanged. This does not check step order or conditions.")
    lines.append("Compare the same query and inputs under similar conditions; one run does not prove an improvement.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compare two saved PostgreSQL JSON plans offline.")
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    try:
        before = PlanReport(json.loads(args.before.read_text(encoding="utf-8-sig")))
        after = PlanReport(json.loads(args.after.read_text(encoding="utf-8-sig")))
        print(f"Before: {args.before}")
        print(f"After: {args.after}")
        print(compare_reports(before, after))
    except (OSError, ValueError, RecursionError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
