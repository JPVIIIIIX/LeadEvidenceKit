"""Read a local JSON report and print Markdown; no network or CRM access."""
import argparse
import json
import sys
from pathlib import Path
from .report import render_markdown, validate_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--check", action="store_true", help="Validate without rendering")
    args = parser.parse_args()
    try:
        report = json.loads(args.input.read_text(encoding="utf-8"))
        errors = validate_report(report)
        if errors:
            raise ValueError("; ".join(errors))
        print("Valid report structure (truth not verified)." if args.check else render_markdown(report))
    except (OSError, ValueError) as exc:
        print(f"leadevidencekit: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
