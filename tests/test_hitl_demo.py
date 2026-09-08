"""Tests for HITL fixture scanner and demo outputs."""

import csv
import json
from pathlib import Path

import pytest

from scanner.fixture_scan import DEFAULT_FIXTURE_DIR, load_manifest, scan_fixtures

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT / "fixtures" / "sample-dataroom"


class TestFixtureManifest:
    def test_manifest_exists_and_lists_files(self):
        manifest = load_manifest(FIXTURE_DIR)
        assert manifest["company"] == "VertiGreen Robotics"
        assert len(manifest["files"]) >= 5

    def test_all_manifest_files_exist(self):
        manifest = load_manifest(FIXTURE_DIR)
        for entry in manifest["files"]:
            path = FIXTURE_DIR / entry["path"]
            assert path.exists(), f"Missing fixture: {entry['path']}"


class TestFixtureScan:
    def test_scan_produces_findings(self):
        result = scan_fixtures(FIXTURE_DIR, run_id="test-run")
        assert result.run_id == "test-run"
        assert len(result.findings) == 9
        labels = {f.label for f in result.findings}
        assert "auto_ok" in labels
        assert "needs_human" in labels
        assert "unclear" in labels

    def test_findings_have_reasoning_steps(self):
        result = scan_fixtures(FIXTURE_DIR)
        for f in result.findings:
            assert f.finding_id
            assert f.reasoning_steps
            assert f.rule_fired


class TestHitlDemoOutputs:
    def test_hitl_demo_writes_outputs(self, tmp_path):
        import subprocess
        import sys

        proc = subprocess.run(
            [sys.executable, "scripts/hitl_demo.py", "--out-dir", str(tmp_path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr

        findings = tmp_path / "findings.json"
        explainer = tmp_path / "notion" / "explainer.md"
        decisions_csv = tmp_path / "notion" / "decisions.csv"
        decisions_json = tmp_path / "notion" / "decisions.json"

        assert findings.exists()
        assert explainer.exists()
        assert decisions_csv.exists()
        assert decisions_json.exists()

        data = json.loads(findings.read_text())
        assert data["summary"]["total"] == 9

        explainer_text = explainer.read_text()
        assert "## Background" in explainer_text
        assert "## Intuition" in explainer_text
        assert "## Literate walkthrough" in explainer_text
        assert "## Quiz" in explainer_text
        assert "Approved only if quiz passed or waived" in explainer_text

        with decisions_csv.open() as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 9
        assert "Finding ID" in rows[0]
        assert rows[0]["Status"] == "pending"
