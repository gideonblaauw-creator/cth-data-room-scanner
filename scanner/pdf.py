"""
scanner/pdf.py
HTML → PDF using Playwright (headless Chromium).
Primary: Playwright Chromium. Fallback: WeasyPrint.
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def render_pdf(html_path: str, pdf_path: str) -> bool:
    """
    Convert an HTML file to PDF using Playwright (headless Chromium).
    Returns True on success, False on failure.

    Install:
        pip install playwright --break-system-packages
        playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("pdf: playwright not installed — try: pip install playwright")
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--font-render-hinting=none",
                "--disable-font-subpixel-positioning",
            ])
            page = browser.new_page(device_scale_factor=2)
            page.goto(
                f"file://{Path(html_path).absolute()}",
                wait_until="networkidle",
                timeout=30000,
            )

            # Expand all collapsible pillar sections before printing
            page.evaluate("""() => {
                document.querySelectorAll('.pillar-body').forEach(el => el.classList.add('open'));
                document.querySelectorAll('.pillar-header').forEach(el => el.classList.add('open'));
            }""")

            # Wait for fonts to load
            page.evaluate_handle("document.fonts.ready")
            page.wait_for_timeout(1500)

            page.pdf(
                path=str(Path(pdf_path).absolute()),
                format="A4",
                print_background=True,
                margin={
                    "top": "0.45in",
                    "bottom": "0.45in",
                    "left": "0.5in",
                    "right": "0.5in",
                },
            )
            browser.close()

        logger.info("pdf: Playwright conversion succeeded → %s", pdf_path)
        print(f"PDF saved → {pdf_path}")
        return True

    except Exception as exc:
        logger.warning("pdf: Playwright error: %s", exc)
        return False


def render_pdf_weasyprint(html_path: str, pdf_path: str) -> bool:
    """
    Fallback: WeasyPrint for environments without Chrome/Chromium.
    Requires: pip install weasyprint --break-system-packages
    Note: expand all pillar sections in HTML before calling (JS won't run).
    """
    try:
        import weasyprint
        logging.getLogger("weasyprint").setLevel(logging.ERROR)
        logging.getLogger("fonttools").setLevel(logging.ERROR)

        html = weasyprint.HTML(filename=html_path)
        doc = html.render()
        print(f"Pages: {len(doc.pages)}")
        doc.write_pdf(pdf_path)
        print(f"PDF saved → {pdf_path}")
        return True

    except ImportError:
        logger.warning("pdf: weasyprint not installed")
        return False
    except Exception as e:
        logger.warning("pdf: WeasyPrint failed: %s", e)
        return False


def convert(html_path: str, pdf_path: str) -> bool:
    """Try Playwright first, then WeasyPrint fallback."""
    if render_pdf(html_path, pdf_path):
        return True
    logger.info("pdf: Playwright failed, trying WeasyPrint fallback")
    return render_pdf_weasyprint(html_path, pdf_path)
