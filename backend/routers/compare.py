from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ..models import PlanComparison, LeafOrderDiff
from ..storage import load_all_leaves, load_all_plans
from ..sorting import evaluate_plan

router = APIRouter(prefix="/compare", tags=["方案比对"])


@router.get("/plans", response_model=PlanComparison)
def compare_two_plans(
    plan_a_id: str = Query(..., description="方案A ID"),
    plan_b_id: str = Query(..., description="方案B ID"),
):
    plans = load_all_plans()
    leaves = load_all_leaves()

    if plan_a_id not in plans:
        raise HTTPException(status_code=404, detail=f"方案 '{plan_a_id}' 不存在")
    if plan_b_id not in plans:
        raise HTTPException(status_code=404, detail=f"方案 '{plan_b_id}' 不存在")

    plan_a = plans[plan_a_id]
    plan_b = plans[plan_b_id]

    leaves_a_sorted = sorted(plan_a.leaves, key=lambda l: l.order)
    leaves_b_sorted = sorted(plan_b.leaves, key=lambda l: l.order)

    map_a = {l.leaf_id: l for l in leaves_a_sorted}
    map_b = {l.leaf_id: l for l in leaves_b_sorted}

    ids_a = set(map_a.keys())
    ids_b = set(map_b.keys())

    common = list(ids_a & ids_b)
    only_a = list(ids_a - ids_b)
    only_b = list(ids_b - ids_a)

    order_diffs: List[LeafOrderDiff] = []
    disputed: List[str] = []

    for leaf_id in common:
        pl_a = map_a[leaf_id]
        pl_b = map_b[leaf_id]
        position_changed = pl_a.order != pl_b.order
        flipped_changed = pl_a.flipped != pl_b.flipped
        is_disputed = False
        dispute_reason = ""

        if position_changed:
            distance = abs(pl_a.order - pl_b.order)
            if distance >= 2:
                is_disputed = True
                dispute_reason = f"位置差异过大（相差 {distance} 位）"
            elif len(common) > 0:
                idx_a = [l.leaf_id for l in leaves_a_sorted].index(leaf_id)
                idx_b = [l.leaf_id for l in leaves_b_sorted].index(leaf_id)
                neighbors_a = set()
                if idx_a > 0:
                    neighbors_a.add(leaves_a_sorted[idx_a - 1].leaf_id)
                if idx_a < len(leaves_a_sorted) - 1:
                    neighbors_a.add(leaves_a_sorted[idx_a + 1].leaf_id)
                neighbors_b = set()
                if idx_b > 0:
                    neighbors_b.add(leaves_b_sorted[idx_b - 1].leaf_id)
                if idx_b < len(leaves_b_sorted) - 1:
                    neighbors_b.add(leaves_b_sorted[idx_b + 1].leaf_id)
                if len(neighbors_a & neighbors_b) == 0:
                    is_disputed = True
                    dispute_reason = "相邻叶片完全不同"

        if flipped_changed and not is_disputed:
            is_disputed = True
            dispute_reason = "翻面状态不同"

        leaf_obj = leaves.get(leaf_id)
        if leaf_obj and not leaf_obj.confirmed and not is_disputed:
            if position_changed or flipped_changed:
                is_disputed = True
                if dispute_reason:
                    dispute_reason += "；"
                dispute_reason += "叶片信息未确认"

        if is_disputed:
            disputed.append(leaf_id)

        order_diffs.append(
            LeafOrderDiff(
                leaf_id=leaf_id,
                order_a=pl_a.order,
                order_b=pl_b.order,
                position_changed=position_changed,
                flipped_changed=flipped_changed,
                is_disputed=is_disputed,
                dispute_reason=dispute_reason,
            )
        )

    only_a_sorted = sorted(only_a, key=lambda lid: map_a[lid].order)
    only_b_sorted = sorted(only_b, key=lambda lid: map_b[lid].order)
    for leaf_id in only_a_sorted:
        order_diffs.append(
            LeafOrderDiff(
                leaf_id=leaf_id,
                order_a=map_a[leaf_id].order,
                order_b=None,
                position_changed=True,
                flipped_changed=False,
                is_disputed=True,
                dispute_reason="仅存在于方案A",
            )
        )
        disputed.append(leaf_id)
    for leaf_id in only_b_sorted:
        order_diffs.append(
            LeafOrderDiff(
                leaf_id=leaf_id,
                order_a=None,
                order_b=map_b[leaf_id].order,
                position_changed=True,
                flipped_changed=False,
                is_disputed=True,
                dispute_reason="仅存在于方案B",
            )
        )
        disputed.append(leaf_id)

    order_diffs.sort(
        key=lambda d: (
            d.order_a if d.order_a is not None else 9999,
            d.order_b if d.order_b is not None else 9999,
        )
    )

    score_a = plan_a.score
    if score_a is None:
        score_a = evaluate_plan(plan_a.leaves, leaves)
    score_b = plan_b.score
    if score_b is None:
        score_b = evaluate_plan(plan_b.leaves, leaves)

    return PlanComparison(
        plan_a_id=plan_a_id,
        plan_b_id=plan_b_id,
        plan_a_name=plan_a.name,
        plan_b_name=plan_b.name,
        plan_a_score=score_a,
        plan_b_score=score_b,
        score_diff=round(score_b - score_a, 4) if score_a is not None and score_b is not None else None,
        common_leaves=sorted(common),
        only_in_a=only_a_sorted,
        only_in_b=only_b_sorted,
        order_diffs=order_diffs,
        disputed_leaves=disputed,
    )


@router.get("/plans/{plan_a_id}/{plan_b_id}/export")
def export_comparison_report(
    plan_a_id: str,
    plan_b_id: str,
    format: str = Query("json", description="导出格式：json 或 text"),
):
    comparison = compare_two_plans(plan_a_id, plan_b_id)

    if format == "text":
        lines = []
        lines.append("=" * 60)
        lines.append("贝叶经叶片复原方案对比报告")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"方案A: {comparison.plan_a_name} ({comparison.plan_a_id})")
        lines.append(f"方案B: {comparison.plan_b_name} ({comparison.plan_b_id})")
        lines.append("")
        lines.append("--- 评分对比 ---")
        lines.append(f"方案A评分: {comparison.plan_a_score}")
        lines.append(f"方案B评分: {comparison.plan_b_score}")
        if comparison.score_diff is not None:
            diff_text = "B更高" if comparison.score_diff > 0 else "A更高" if comparison.score_diff < 0 else "相同"
            lines.append(f"评分差异: {comparison.score_diff} ({diff_text})")
        lines.append("")
        lines.append("--- 叶片集合 ---")
        lines.append(f"共有叶片: {len(comparison.common_leaves)} 片")
        lines.append(f"仅方案A: {len(comparison.only_in_a)} 片 - {', '.join(comparison.only_in_a) or '无'}")
        lines.append(f"仅方案B: {len(comparison.only_in_b)} 片 - {', '.join(comparison.only_in_b) or '无'}")
        lines.append("")
        lines.append("--- 顺序差异详情 ---")
        for d in comparison.order_diffs:
            pos_a = str(d.order_a + 1) if d.order_a is not None else "-"
            pos_b = str(d.order_b + 1) if d.order_b is not None else "-"
            flag = " ⚠争议" if d.is_disputed else ""
            changes = []
            if d.position_changed:
                changes.append("位置变化")
            if d.flipped_changed:
                changes.append("翻面变化")
            change_text = f" [{'、'.join(changes)}]" if changes else ""
            lines.append(f"  {d.leaf_id}: A#{pos_a} → B#{pos_b}{change_text}{flag}")
            if d.dispute_reason:
                lines.append(f"         原因: {d.dispute_reason}")
        lines.append("")
        lines.append(f"--- 争议叶片 ({len(comparison.disputed_leaves)} 片) ---")
        lines.append(", ".join(comparison.disputed_leaves) or "无")
        lines.append("")
        lines.append("=" * 60)
        report_text = "\n".join(lines)
        return JSONResponse(
            content={"report": report_text},
            headers={
                "Content-Disposition": f"attachment; filename=comparison_{plan_a_id}_vs_{plan_b_id}.txt"
            },
        )

    return comparison
