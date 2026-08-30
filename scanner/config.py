"""
scanner/config.py
Central configuration — all paths and IDs are env-driven, no hardcoded host paths.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo root (parent of scanner/)
REPO_ROOT = Path(__file__).resolve().parent.parent

# BeCaps calibration folder — READ-ONLY, never write
BECAPS_CALIBRATION_FOLDER_ID = "1sg4TlFoP2_YVYmDdxuacC3Gs4kpB0Bd_"

# Default CTH reports output folder
DEFAULT_REPORTS_FOLDER_ID = "1RvuoSvbm6SvbdCWU06Wa7jyfEniPmzbP"

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(REPO_ROOT / "output")))
SKILLS_DIR = Path(os.getenv("SKILLS_DIR", str(REPO_ROOT / "skills")))
TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", str(REPO_ROOT / "templates")))

DRIVE_REPORTS_FOLDER_ID = os.getenv(
    "DRIVE_REPORTS_FOLDER_ID", DEFAULT_REPORTS_FOLDER_ID
)

# Google Drive API — service account JSON path (never commit the key)
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

# LLM for headless scoring
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# HTTP app
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8080"))

# Redis / RQ
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
RQ_QUEUE_NAME = os.getenv("RQ_QUEUE_NAME", "cth-scans")

# Seller legal entity (report footer)
SELLER_LEGAL_NAME = os.getenv(
    "SELLER_LEGAL_NAME", "CLEANTECHHUB INTERNATIONAL S.L."
)


def assert_not_becaps_folder(folder_id: str, operation: str = "write") -> None:
    """Guard: BeCaps calibration folder is read-only."""
    if folder_id == BECAPS_CALIBRATION_FOLDER_ID:
        raise PermissionError(
            f"BeCaps calibration folder ({BECAPS_CALIBRATION_FOLDER_ID}) is "
            f"read-only — cannot {operation}."
        )


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR
