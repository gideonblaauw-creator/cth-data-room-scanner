#!/usr/bin/env python3
"""
scripts/dry_run.py
Dry-run the scan pipeline without Drive API or LLM calls.
Uses BeCaps 3.5 calibration fixture for scoring; generates local HTML + PDF.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scanner.runner import ScanRequest, run_scan


def main():
    parser = argparse.ArgumentParser(description="CTH Scanner dry-run (no API keys)")
    parser.add_argument("--company", default="TestCo", help="Company name")
    parser.add_argument("--lang", default="es", choices=["es", "en"])
    parser.add_argument(
        "--folder-id",
        default="dry-run-folder-id",
        help="Fake Drive folder ID for the request",
    )
    args = parser.parse_args()

    req = ScanRequest(
        drive_url_or_id=args.folder_id,
        company_name=args.company,
        lang=args.lang,
        dry_run=True,
    )

    print("Running dry-run scan (BeCaps calibration fixture, no upload)...")
    result = run_scan(req)
    print(result.summary())

    if result.errors:
        print("\nWarnings:")
        for e in result.errors:
            print(f"  - {e}")
        sys.exit(1 if "failed" in " ".join(result.errors).lower() else 0)

    # Verify outputs exist
    html = Path(result.html_path)
    if not html.exists():
        print(f"ERROR: HTML not found at {html}")
        sys.exit(1)
    print(f"\n✓ HTML: {html} ({html.stat().st_size} bytes)")

    if result.pdf_path:
        pdf = Path(result.pdf_path)
        if pdf.exists():
            print(f"✓ PDF:  {pdf} ({pdf.stat().st_size} bytes)")
        else:
            print("⚠ PDF not generated (Playwright may not be installed)")
    else:
        print("⚠ PDF not generated")

    sys.exit(0)


if __name__ == "__main__":
    main()
