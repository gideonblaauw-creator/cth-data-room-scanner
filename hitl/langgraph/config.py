"""
Scanner-only Understanding Lab URLs and optional LangSmith tracing config.

URLs come from ticket `lab_notion` — not hardcoded as defaults for other products.
Override via env when running dogfood against a different lab ticket.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ScannerUnderstandingLab:
    """Tier 1–2 Understanding Lab links for cth-data-room-scanner only."""

    context_url: str
    playground_url: str
    shared_decisions_url: str

    def as_dict(self) -> dict[str, str]:
        return {
            "context": self.context_url,
            "playground": self.playground_url,
            "shared_decisions": self.shared_decisions_url,
        }


# Ticket lab_notion (Scanner dogfood t1242u) — override via env, never LexiScan URLs.
_DEFAULT_LAB = ScannerUnderstandingLab(
    context_url="https://app.notion.com/p/3d5dfee50be98174a045febce0fc4b3d",
    playground_url="https://app.notion.com/p/3d9dfee50be981ab8bd4ff5fd40c8e35",
    shared_decisions_url="https://app.notion.com/p/bb52cfa45b6744e59983528480fbab4b",
)


def load_understanding_lab() -> ScannerUnderstandingLab:
    return ScannerUnderstandingLab(
        context_url=os.getenv("SCANNER_LAB_CONTEXT_URL", _DEFAULT_LAB.context_url),
        playground_url=os.getenv("SCANNER_LAB_PLAYGROUND_URL", _DEFAULT_LAB.playground_url),
        shared_decisions_url=os.getenv(
            "SCANNER_LAB_SHARED_DECISIONS_URL", _DEFAULT_LAB.shared_decisions_url
        ),
    )


def langsmith_tracing_enabled() -> bool:
    """Tracing is opt-in; keys live in Infisical, not in repo."""
    return bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))


def configure_langsmith_project(project: str = "cth-scanner-hitl-dogfood") -> None:
    """Stub tracing hook — no-op unless LANGSMITH_API_KEY / LANGCHAIN_API_KEY set."""
    if not langsmith_tracing_enabled():
        return
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", project)
