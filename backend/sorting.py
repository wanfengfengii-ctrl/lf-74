import math
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from .models import Leaf, SortRecommendation, SortResult


def compute_hole_alignment_score(leaf_a: Leaf, leaf_b: Leaf, flipped: bool = False) -> float:
    if not leaf_a.holes or not leaf_b.holes:
        return 0.5

    holes_a = [(h.x, h.y) for h in leaf_a.holes]
    holes_b = []
    for h in leaf_b.holes:
        if flipped:
            holes_b.append((leaf_b.width - h.x, h.y))
        else:
            holes_b.append((h.x, h.y))

    total_pairs = 0
    total_distance = 0.0

    min_holes = min(len(holes_a), len(holes_b))
    for i in range(min_holes):
        x1, y1 = holes_a[i]
        x2, y2 = holes_b[i]
        dist = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
        max_dim = max(leaf_a.length, leaf_a.width, leaf_b.length, leaf_b.width)
        normalized = 1.0 - min(dist / (max_dim / 2.0), 1.0)
        total_distance += normalized
        total_pairs += 1

    if total_pairs == 0:
        return 0.5

    return total_distance / total_pairs


def compute_text_continuity_score(leaf_a: Leaf, leaf_b: Leaf) -> float:
    text_a = leaf_a.residual_text.strip()
    text_b = leaf_b.residual_text.strip()

    if not text_a or not text_b:
        return 0.3

    overlap_score = 0.0
    max_overlap = min(len(text_a), len(text_b), 8)
    for overlap_len in range(max_overlap, 0, -1):
        if text_a.endswith(text_b[:overlap_len]):
            overlap_score = overlap_len / max(len(text_a), len(text_b)) * 2
            break
        if text_b.startswith(text_a[-overlap_len:]):
            overlap_score = overlap_len / max(len(text_a), len(text_b)) * 2
            break

    similarity = SequenceMatcher(None, text_a[-8:], text_b[:8]).ratio()

    return min(overlap_score * 0.6 + similarity * 0.4, 1.0)


def compute_combined_score(
    hole_score: float,
    text_score: float,
    hole_weight: float = 0.5,
    text_weight: float = 0.5,
) -> float:
    return hole_score * hole_weight + text_score * text_weight


def recommend_next_leaf(
    current_leaf: Leaf,
    candidates: List[Leaf],
    hole_weight: float = 0.5,
    text_weight: float = 0.5,
) -> List[SortRecommendation]:
    results = []
    for candidate in candidates:
        if candidate.id == current_leaf.id:
            continue

        hole_score_normal = compute_hole_alignment_score(current_leaf, candidate, flipped=False)
        hole_score_flipped = compute_hole_alignment_score(current_leaf, candidate, flipped=True)
        hole_score = max(hole_score_normal, hole_score_flipped)

        text_score = compute_text_continuity_score(current_leaf, candidate)

        combined = compute_combined_score(hole_score, text_score, hole_weight, text_weight)

        reasons = []
        if hole_score >= 0.7:
            reasons.append(f"孔位对齐度高({hole_score:.2f})")
        elif hole_score >= 0.4:
            reasons.append(f"孔位对齐度中等({hole_score:.2f})")
        else:
            reasons.append(f"孔位对齐度低({hole_score:.2f})")

        if text_score >= 0.5:
            reasons.append(f"残文连续性好({text_score:.2f})")
        elif text_score >= 0.3:
            reasons.append(f"残文连续性一般({text_score:.2f})")
        else:
            reasons.append(f"残文连续性弱({text_score:.2f})")

        if hole_score_flipped > hole_score_normal:
            reasons.append("建议翻面")

        results.append(
            SortRecommendation(
                leaf_id=candidate.id,
                score=round(combined, 4),
                hole_alignment_score=round(hole_score, 4),
                text_continuity_score=round(text_score, 4),
                reason="；".join(reasons),
            )
        )

    results.sort(key=lambda x: x.score, reverse=True)
    return results


def sort_all_leaves(
    leaves: Dict[str, Leaf],
    start_leaf_id: Optional[str] = None,
    hole_weight: float = 0.5,
    text_weight: float = 0.5,
) -> SortResult:
    if not leaves:
        return SortResult(ordered_leaves=[], total_score=0.0)

    remaining = set(leaves.keys())
    ordered: List[SortRecommendation] = []
    total_score = 0.0

    if start_leaf_id and start_leaf_id in leaves:
        current_id = start_leaf_id
    else:
        current_id = max(
            leaves.keys(),
            key=lambda lid: (
                len(leaves[lid].holes),
                len(leaves[lid].residual_text),
            ),
        )

    remaining.remove(current_id)
    ordered.append(
        SortRecommendation(
            leaf_id=current_id,
            score=1.0,
            hole_alignment_score=1.0,
            text_continuity_score=1.0,
            reason="起始叶片",
        )
    )

    while remaining:
        current_leaf = leaves[current_id]
        candidate_list = [leaves[rid] for rid in remaining]

        recommendations = recommend_next_leaf(
            current_leaf, candidate_list, hole_weight, text_weight
        )

        if not recommendations:
            break

        best = recommendations[0]
        ordered.append(best)
        total_score += best.score
        remaining.remove(best.leaf_id)
        current_id = best.leaf_id

    avg_score = total_score / max(len(ordered) - 1, 1) if ordered else 0.0
    return SortResult(ordered_leaves=ordered, total_score=round(avg_score, 4))


def evaluate_plan(plan_leaves: List, all_leaves: Dict[str, Leaf]) -> float:
    if len(plan_leaves) < 2:
        return 1.0 if plan_leaves else 0.0

    total_score = 0.0
    valid_pairs = 0

    sorted_plan = sorted(plan_leaves, key=lambda pl: pl.order)
    for i in range(len(sorted_plan) - 1):
        a_id = sorted_plan[i].leaf_id
        b_id = sorted_plan[i + 1].leaf_id
        if a_id in all_leaves and b_id in all_leaves:
            leaf_a = all_leaves[a_id]
            leaf_b = all_leaves[b_id]
            hole_score = compute_hole_alignment_score(leaf_a, leaf_b, sorted_plan[i + 1].flipped)
            text_score = compute_text_continuity_score(leaf_a, leaf_b)
            total_score += compute_combined_score(hole_score, text_score)
            valid_pairs += 1

    return round(total_score / max(valid_pairs, 1), 4) if valid_pairs else 0.0
