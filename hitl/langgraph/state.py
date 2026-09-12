"""Typed state for the Scanner HITL review LangGraph."""

from __future__ import annotations

from typing import Any, TypedDict


class ReviewGraphState(TypedDict, total=False):
    job_id: str
    findings_path: str
    findings_doc: dict[str, Any]
    understanding_lab: dict[str, str]
    pending: list[dict[str, Any]]
    human_payload: dict[str, Any]
    locks_doc: dict[str, Any]
    locks_path: str
    status: str
