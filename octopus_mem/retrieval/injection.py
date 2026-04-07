from dataclasses import dataclass
from math import pow
from typing import Sequence


@dataclass(frozen=True)
class Candidate:
    id: str
    content: str
    score: float
    recency_days: int
    kind: str
    token_count: int


@dataclass(frozen=True)
class InjectionPlan:
    selected: tuple[Candidate, ...]
    rejected: tuple[tuple[Candidate, str], ...]
    used_tokens: int
    budget_tokens: int


def plan_injection(
    candidates: Sequence[Candidate],
    *,
    budget_tokens: int,
    pin_kinds: tuple[str, ...] = ("open_question",),
    decay_half_life_days: float = 7.0,
) -> InjectionPlan:
    allowed_kinds = {"decision", "fact", "open_question", "summary"}
    seen_ids: set[str] = set()
    selected: list[Candidate] = []
    rejected: list[tuple[Candidate, str]] = []
    scored_candidates: list[tuple[float, int, Candidate]] = []
    used_tokens = 0

    for index, candidate in enumerate(candidates):
        if candidate.id in seen_ids:
            rejected.append((candidate, "duplicate_id"))
            continue
        seen_ids.add(candidate.id)

        if candidate.kind not in allowed_kinds:
            rejected.append((candidate, "unknown_kind"))
            continue

        if candidate.kind in pin_kinds:
            if used_tokens + candidate.token_count <= budget_tokens:
                selected.append(candidate)
                used_tokens += candidate.token_count
            else:
                rejected.append((candidate, "budget"))
            continue

        effective = candidate.score * pow(0.5, candidate.recency_days / decay_half_life_days)
        scored_candidates.append((effective, index, candidate))

    for effective, index, candidate in sorted(scored_candidates, key=lambda item: (-item[0], item[1])):
        if effective <= 0:
            rejected.append((candidate, "low_score"))
            continue
        if used_tokens + candidate.token_count <= budget_tokens:
            selected.append(candidate)
            used_tokens += candidate.token_count
        else:
            rejected.append((candidate, "budget"))

    return InjectionPlan(
        selected=tuple(selected),
        rejected=tuple(rejected),
        used_tokens=used_tokens,
        budget_tokens=budget_tokens,
    )
