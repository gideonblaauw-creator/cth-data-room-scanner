"""Tests for review lock merge and path helpers."""

from __future__ import annotations

from pathlib import Path

from scanner.review_persistence import locks_path_for_job, merge_lock_records


class TestMergeLockRecords:
    def test_server_wins_on_newer_locked_at(self):
        server = [{
            "finding_id": "S001",
            "fixture_path": "x",
            "agent_suggestion": "a",
            "human_decision": "agree",
            "rationale": "server newer",
            "status": "reviewed",
            "locked_at": "2026-09-12T15:00:00+00:00",
        }]
        local = [{
            "finding_id": "S001",
            "fixture_path": "x",
            "agent_suggestion": "a",
            "human_decision": "override",
            "rationale": "local older",
            "status": "reviewed",
            "locked_at": "2026-09-12T14:00:00+00:00",
        }]
        merged, conflicts = merge_lock_records(server, local)
        assert len(merged) == 1
        assert merged[0]["human_decision"] == "agree"

    def test_local_wins_when_newer(self):
        server = [{
            "finding_id": "S001",
            "fixture_path": "x",
            "agent_suggestion": "a",
            "human_decision": "agree",
            "rationale": "server older",
            "status": "reviewed",
            "locked_at": "2026-09-12T14:00:00+00:00",
        }]
        local = [{
            "finding_id": "S001",
            "fixture_path": "x",
            "agent_suggestion": "a",
            "human_decision": "override",
            "rationale": "local newer",
            "status": "reviewed",
            "locked_at": "2026-09-12T15:00:00+00:00",
        }]
        merged, _ = merge_lock_records(server, local)
        assert merged[0]["human_decision"] == "override"

    def test_union_of_distinct_findings(self):
        server = [{"finding_id": "S001", "locked_at": "2026-09-12T14:00:00+00:00",
                   "fixture_path": "a", "agent_suggestion": "x", "human_decision": "agree",
                   "rationale": "one two three four", "status": "reviewed"}]
        local = [{"finding_id": "S002", "locked_at": "2026-09-12T14:00:01+00:00",
                  "fixture_path": "b", "agent_suggestion": "y", "human_decision": "defer",
                  "rationale": "five six seven eight", "status": "reviewed"}]
        merged, _ = merge_lock_records(server, local)
        assert {m["finding_id"] for m in merged} == {"S001", "S002"}


class TestLocksPathForJob:
    def test_job_based_filename(self, tmp_path):
        p = locks_path_for_job("becaps", tmp_path)
        assert p == tmp_path / "becaps-review-locks.json"

    def test_sanitizes_slashes(self, tmp_path):
        p = locks_path_for_job("foo/bar", tmp_path)
        assert p.name == "foo_bar-review-locks.json"
