#!/usr/bin/env python3
"""
scripts/review_demo.py
Generate production findings from BeCaps scoring fixture (or fixture scan) for local review.

Usage:
  python scripts/review_demo.py              # BeCaps → output/becaps-demo-2026-09.findings.json
  python scripts/review_demo.py --fixture    # VertiGreen fixture → out/findings.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scanner.config import OUTPUT_DIR, REPO_ROOT
from scanner.findings_from_score import (
    findings_from_score,
    findings_output_path,
    save_findings,
)
from scanner.fixture_scan import scan_fixtures
from scanner.score_runner import load_becaps_fixture


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate findings for production review UI")
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Use VertiGreen fixture scan (F-prefixed IDs) instead of BeCaps scoring",
    )
    parser.add_argument(
        "--company",
        default="BeCaps",
        help="Company name for BeCaps demo (default: BeCaps)",
    )
    args = parser.parse_args()

    if args.fixture:
        out_dir = REPO_ROOT / "out"
        out_dir.mkdir(exist_ok=True)
        scan_out = scan_fixtures()
        path = out_dir / "findings.json"
        import json

        path.write_text(json.dumps(scan_out.to_dict(), indent=2) + "\n", encoding="utf-8")
        print(f"✓ Fixture findings: {path} ({len(scan_out.findings)} findings)")
        print(f"\nOpen review UI:")
        print(f"  make up  # or: flask run")
        print(f"  http://127.0.0.1:8080/review/demo?path=out/findings.json")
        return 0

    scoring = load_becaps_fixture()
    scoring["company"]["name"] = args.company
    doc = findings_from_score(scoring, source="dry_run", run_id="becaps-demo")
    path = findings_output_path("becaps-demo", doc["scan_date"][:10], OUTPUT_DIR)
    save_findings(doc, path)

    print(f"✓ Score findings: {path}")
    print(f"  Total: {doc['summary']['total']} "
          f"(needs_human={doc['summary']['needs_human']}, "
          f"unclear={doc['summary']['unclear']}, "
          f"auto_ok={doc['summary']['auto_ok']})")
    print(f"\nOpen review UI:")
    print(f"  http://127.0.0.1:8080/review/becaps")
    print(f"  or: http://127.0.0.1:8080/review/demo?path={path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
