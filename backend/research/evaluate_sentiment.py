import argparse
import json
from pathlib import Path

from app.core.config import Settings
from research.phrasebank import (
    DEFAULT_CONFIG,
    PhraseBankUnavailableError,
    evaluate_phrasebank,
    render_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the configured RiskPulse sentiment analyzer on Financial PhraseBank")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="PhraseBank agreement configuration")
    parser.add_argument("--local-path", help="Optional local CSV, JSON, JSONL, or dataset directory")
    parser.add_argument("--output", default="research/reports/financial_phrasebank_latest.json", help="JSON report path")
    parser.add_argument("--summary", default="research/reports/financial_phrasebank_latest.txt", help="Human-readable summary path")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    try:
        report = evaluate_phrasebank(Settings(), config=args.config, local_path=args.local_path, seed=args.seed)
    except PhraseBankUnavailableError as exc:
        print(f"EVALUATION SKIPPED: {exc}")
        return 2

    output_path = Path(args.output)
    summary_path = Path(args.summary)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(render_summary(report), encoding="utf-8")
    print(render_summary(report), end="")
    print(f"JSON report: {output_path}")
    print(f"Summary report: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
