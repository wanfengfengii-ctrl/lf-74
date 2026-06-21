from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from ..models import (
    ReconstructionPlan,
    ReconstructionPlanCreate,
    ReconstructionPlanUpdate,
)
from ..sorting import evaluate_plan
from ..storage import load_all_leaves, load_all_plans, save_all_plans

router = APIRouter(prefix="/plans", tags=["复原方案管理"])


@router.get("", response_model=List[ReconstructionPlan])
def list_plans():
    plans = load_all_plans()
    return sorted(plans.values(), key=lambda p: p.created_at, reverse=True)


@router.get("/{plan_id}", response_model=ReconstructionPlan)
def get_plan(plan_id: str):
    plans = load_all_plans()
    if plan_id not in plans:
        raise HTTPException(status_code=404, detail=f"复原方案 '{plan_id}' 不存在")
    return plans[plan_id]


def _validate_plan_leaves(plan: ReconstructionPlan) -> ReconstructionPlan:
    leaves = load_all_leaves()
    leaf_ids = [l.leaf_id for l in plan.leaves]
    for lid in leaf_ids:
        if lid not in leaves:
            raise HTTPException(status_code=400, detail=f"叶片 '{lid}' 不存在")

    if plan.is_final:
        unconfirmed = [lid for lid in leaf_ids if not leaves[lid].confirmed]
        if unconfirmed:
            raise HTTPException(
                status_code=400,
                detail=f"存在未确认的叶片: {', '.join(unconfirmed)}，不能标记为最终方案",
            )

    plan.score = evaluate_plan(plan.leaves, leaves)
    return plan


@router.post("", response_model=ReconstructionPlan)
def create_plan(plan_data: ReconstructionPlanCreate):
    plans = load_all_plans()
    if plan_data.id in plans:
        raise HTTPException(status_code=400, detail=f"复原方案编号 '{plan_data.id}' 已存在")

    now = datetime.now()
    try:
        plan = ReconstructionPlan(
            **plan_data.model_dump(),
            created_at=now,
            updated_at=now,
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)

    plan = _validate_plan_leaves(plan)
    plans[plan.id] = plan
    save_all_plans(plans)
    return plan


@router.put("/{plan_id}", response_model=ReconstructionPlan)
def update_plan(plan_id: str, plan_data: ReconstructionPlanUpdate):
    plans = load_all_plans()
    if plan_id not in plans:
        raise HTTPException(status_code=404, detail=f"复原方案 '{plan_id}' 不存在")

    existing = plans[plan_id]
    update_data = plan_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(existing, field, value)

    existing.updated_at = datetime.now()

    try:
        existing = ReconstructionPlan.model_validate(existing.model_dump())
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)

    existing = _validate_plan_leaves(existing)

    plans[plan_id] = existing
    save_all_plans(plans)
    return existing


@router.delete("/{plan_id}")
def delete_plan(plan_id: str):
    plans = load_all_plans()
    if plan_id not in plans:
        raise HTTPException(status_code=404, detail=f"复原方案 '{plan_id}' 不存在")
    del plans[plan_id]
    save_all_plans(plans)
    return {"message": f"复原方案 '{plan_id}' 已删除"}


@router.post("/{plan_id}/recalculate", response_model=ReconstructionPlan)
def recalculate_plan_score(plan_id: str):
    plans = load_all_plans()
    if plan_id not in plans:
        raise HTTPException(status_code=404, detail=f"复原方案 '{plan_id}' 不存在")

    plan = plans[plan_id]
    leaves = load_all_leaves()
    plan.score = evaluate_plan(plan.leaves, leaves)
    plan.updated_at = datetime.now()

    plans[plan_id] = plan
    save_all_plans(plans)
    return plan
