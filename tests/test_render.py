"""Tests for scanner/render.py"""

import json
from pathlib import Path

from scanner.render import render_report, slugify, save_html
from scanner.score_runner import load_becaps_fixture


class TestSlugify:
    def test_basic(self):
        assert slugify("BeCaps S.A.") == "becaps-s-a"

    def test_unicode(self):
        assert slugify("Empresa Española") == "empresa-espa-ola"


class TestRenderReport:
    def test_renders_becaps_fixture(self, tmp_path):
        scoring = load_becaps_fixture()
        html = render_report(scoring, lang="es")

        assert "BeCaps" in html
        assert "3.5" in html
        assert "{{company_name}}" not in html  # all placeholders replaced
        assert "CLEANTECHHUB INTERNATIONAL S.L." in html

    def test_save_html(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        scoring = load_becaps_fixture()
        html = render_report(scoring)
        path = save_html(html, "becaps", "2026-04-15", output_dir=str(tmp_path / "output"))

        assert Path(path).exists()
        content = Path(path).read_text()
        assert len(content) > 1000
