import json
from pathlib import Path

import pytest

from octopus_mem.retrieval.injection import Candidate, plan_injection


def _candidate(**overrides):
    data = {
        "id": "c1",
        "content": "candidate",
        "score": 0.5,
        "recency_days": 0,
        "kind": "fact",
        "token_count": 10,
    }
    data.update(overrides)
    return Candidate(**data)


def _rejection_map(rejected):
    result = {}
    seen = {}
    for candidate, reason in rejected:
        seen[candidate.id] = seen.get(candidate.id, 0) + 1
        key = candidate.id if seen[candidate.id] == 1 else f"{candidate.id}#{seen[candidate.id]}"
        result[key] = reason
    return result


def test_pin_pass_selects_open_question_before_higher_score_fact():
    plan = plan_injection(
        [
            _candidate(id="q1", kind="open_question", score=0.01, recency_days=30, token_count=20),
            _candidate(id="f1", kind="fact", score=0.99, recency_days=0, token_count=80),
            _candidate(id="f2", kind="fact", score=0.90, recency_days=0, token_count=20),
        ],
        budget_tokens=100,
    )
    assert [c.id for c in plan.selected] == ["q1", "f1"]
    assert _rejection_map(plan.rejected) == {"f2": "budget"}


def test_decay_weighting_prefers_newer_candidate():
    plan = plan_injection(
        [
            _candidate(id="old", score=1.0, recency_days=30, token_count=40),
            _candidate(id="new", score=0.8, recency_days=0, token_count=40),
        ],
        budget_tokens=40,
        pin_kinds=(),
    )
    assert [c.id for c in plan.selected] == ["new"]
    assert _rejection_map(plan.rejected) == {"old": "budget"}


def test_duplicate_and_unknown_candidates_get_specific_reasons():
    plan = plan_injection(
        [
            _candidate(id="d1", kind="decision", score=0.9),
            _candidate(id="d1", kind="decision", score=0.8),
            _candidate(id="x1", kind="mystery", score=0.7),
        ],
        budget_tokens=100,
        pin_kinds=(),
    )
    assert [c.id for c in plan.selected] == ["d1"]
    assert _rejection_map(plan.rejected) == {"d1": "duplicate_id", "x1": "unknown_kind"}


def test_zero_effective_score_gets_low_score_reason():
    plan = plan_injection(
        [
            _candidate(id="z1", score=0.0, token_count=10),
            _candidate(id="f1", score=0.5, token_count=10),
        ],
        budget_tokens=20,
        pin_kinds=(),
    )
    assert [c.id for c in plan.selected] == ["f1"]
    assert _rejection_map(plan.rejected) == {"z1": "low_score"}


@pytest.mark.parametrize("fixture_path", sorted(Path("tests/golden/injection").glob("*.json")))
def test_golden_injection_fixtures(fixture_path):
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    candidates = tuple(Candidate(**candidate) for candidate in fixture["candidates"])
    plan = plan_injection(
        candidates,
        budget_tokens=fixture["budget_tokens"],
        pin_kinds=tuple(fixture.get("pin_kinds", ["open_question"])),
        decay_half_life_days=fixture.get("decay_half_life_days", 7.0),
    )

    assert [candidate.id for candidate in plan.selected] == fixture["expected_selected_ids"]
    assert _rejection_map(plan.rejected) == fixture["expected_rejected_reasons"]
