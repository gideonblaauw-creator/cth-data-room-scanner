"""Integration test for dry-run pipeline."""

from pathlib import Path

from scanner.runner import ScanRequest, run_scan


class TestDryRunPipeline:
    def test_dry_run_generates_html(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
        # Re-import config to pick up env — patch ensure_output_dir via OUTPUT_DIR
        import scanner.config as cfg
        monkeypatch.setattr(cfg, "OUTPUT_DIR", tmp_path)

        req = ScanRequest(
            drive_url_or_id="dry-run-test-folder",
            company_name="DryRun Co",
            lang="es",
            dry_run=True,
        )
        result = run_scan(req)

        assert result.company_name == "DryRun Co"
        assert result.overall_score == 3.5
        assert Path(result.html_path).exists()
        html = Path(result.html_path).read_text()
        assert "DryRun Co" in html
        assert result.drive_folder_url is None  # no upload in dry-run
        assert result.findings_path is not None
        findings = Path(result.findings_path)
        assert findings.exists()
        import json
        doc = json.loads(findings.read_text())
        assert doc["source"] == "dry_run"
        assert len(doc["findings"]) >= 1
        assert doc["findings"][0]["finding_id"].startswith("S")
