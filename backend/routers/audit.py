import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError

from ..models import (
    OperationLog,
    OperationType,
    PlanVersion,
    PlanVersionCreate,
    ReconstructionPlan,
    ReconstructionLeaf,
)
from ..storage import (
    load_operation_logs,
    get_operation_log,
    load_plan_versions,
    get_plan_version,
    save_plan_version,
    get_next_version_number,
    load_all_plans,
    save_all_plans,
    delete_plan_versions,
    add_operation_log,
)
from ..sorting import evaluate_plan
from ..storage import load_all_leaves

router = APIRouter(prefix="/audit", tags=["操作日志与版本"])


@router.get("/logs", response_model=List[OperationLog])
def list_operation_logs(
    target_type: Optional[str] = Query(None, description="对象类型：leaf/plan/annotation"),
    target_id: Optional[str] = Query(None, description="对象ID"),
    operation_type: Optional[str] = Query(None, description="操作类型"),
    limit: int = Query(100, ge=1, le=500),
):
    return load_operation_logs(
        target_type=target_type,
        target_id=target_id,
        operation_type=operation_type,
        limit=limit,
    )


@router.get("/logs/{log_id}", response_model=OperationLog)
def get_single_log(log_id: str):
    log = get_operation_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail=f"日志 '{log_id}' 不存在")
    return log


@router.get("/plans/{plan_id}/versions", response_model=List[PlanVersion])
def list_plan_versions(plan_id: str):
    plans = load_all_plans()
    if plan_id not in plans:
        raise HTTPException(status_code=404, detail=f"方案 '{plan_id}' 不存在")
    return load_plan_versions(plan_id)


@router.get("/versions/{version_id}", response_model=PlanVersion)
def get_single_version(version_id: str):
    version = get_plan_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"版本 '{version_id}' 不存在")
    return version


@router.post("/plans/{plan_id}/versions", response_model=PlanVersion)
def create_plan_version(plan_id: str, data: PlanVersionCreate):
    plans = load_all_plans()
    if plan_id not in plans:
        raise HTTPException(status_code=404, detail=f"方案 '{plan_id}' 不存在")

    plan = plans[plan_id]
    version_num = get_next_version_number(plan_id)

    try:
        leaves_list = [l.model_dump(mode="json") for l in plan.leaves]
        version = PlanVersion(
            id=str(uuid.uuid4()),
            plan_id=plan_id,
            version=version_num,
            name=data.name or f"v{version_num}",
            description=data.description,
            leaves=leaves_list,
            score=plan.score,
            is_final=plan.is_final,
            snapshot_data=plan.model_dump(mode="json"),
            created_at=datetime.now(),
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)

    version = save_plan_version(version)

    add_operation_log(
        operation_type="snapshot",
        target_type="plan",
        target_id=plan_id,
        description=f"创建方案快照: {version.name} (v{version_num})",
        after_data={"version_id": version.id, "version": version_num, "name": version.name},
    )

    return version


@router.post("/versions/{version_id}/restore")
def restore_plan_version(version_id: str):
    version = get_plan_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"版本 '{version_id}' 不存在")

    plans = load_all_plans()
    if version.plan_id not in plans:
        raise HTTPException(status_code=404, detail=f"方案 '{version.plan_id}' 不存在")

    plan = plans[version.plan_id]
    before_data = plan.model_dump(mode="json")

    snapshot = version.snapshot_data
    if snapshot:
        leaves_data = snapshot.get("leaves", [])
    else:
        leaves_data = version.leaves

    leaves_list = []
    for ld in leaves_data:
        if isinstance(ld, dict):
            leaves_list.append(ReconstructionLeaf(**ld))
        else:
            leaves_list.append(ld)

    plan.leaves = leaves_list
    plan.is_final = version.is_final
    plan.updated_at = datetime.now()

    try:
        from pydantic import TypeAdapter
        plan = ReconstructionPlan.model_validate(plan.model_dump())
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)

    all_leaves = load_all_leaves()
    plan.score = evaluate_plan(plan.leaves, all_leaves)

    plans[version.plan_id] = plan
    save_all_plans(plans)

    add_operation_log(
        operation_type=OperationType.RESTORE,
        target_type="plan",
        target_id=version.plan_id,
        description=f"恢复方案到版本 {version.name} (v{version.version})",
        before_data=before_data,
        after_data=plan.model_dump(mode="json"),
    )

    return {"message": f"方案已恢复到版本 {version.name} (v{version.version})", "plan": plan}


@router.delete("/versions/{version_id}")
def delete_plan_version(version_id: str):
    version = get_plan_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"版本 '{version_id}' 不存在")

    import json
    import os
    from ..storage import VERSIONS_FILE

    if os.path.exists(VERSIONS_FILE):
        with open(VERSIONS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            versions_list = json.loads(content) if content else []
    else:
        versions_list = []

    filtered = [v for v in versions_list if v.get("id") != version_id]
    with open(VERSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2, default=str)

    add_operation_log(
        operation_type=OperationType.DELETE,
        target_type="plan",
        target_id=version.plan_id,
        description=f"删除方案版本 {version.name} (v{version.version})",
        before_data={"version_id": version_id, "version": version.version, "name": version.name},
    )

    return {"message": f"版本 {version.name} 已删除"}


@router.get("/plans/{plan_id}/export")
def export_plan_versions_report(plan_id: str):
    plans = load_all_plans()
    if plan_id not in plans:
        raise HTTPException(status_code=404, detail=f"方案 '{plan_id}' 不存在")

    plan = plans[plan_id]
    versions = load_plan_versions(plan_id)
    logs = load_operation_logs(target_type="plan", target_id=plan_id, limit=200)

    lines = []
    lines.append("=" * 60)
    lines.append(f"方案 '{plan.name}' 历史版本与操作日志报告")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"方案编号: {plan.id}")
    lines.append(f"方案名称: {plan.name}")
    if plan.description:
        lines.append(f"方案说明: {plan.description}")
    lines.append(f"当前状态: {'最终方案' if plan.is_final else '草稿方案'}")
    if plan.score is not None:
        lines.append(f"当前评分: {plan.score}")
    lines.append(f"创建时间: {plan.created_at}")
    lines.append(f"更新时间: {plan.updated_at}")
    lines.append("")
    lines.append("--- 版本历史 ---")
    if versions:
        for v in versions:
            score_str = f", 评分: {v.score}" if v.score is not None else ""
            lines.append(f"  [v{v.version}] {v.name} - {v.created_at}{score_str}")
            if v.description:
                lines.append(f"         {v.description}")
    else:
        lines.append("  （暂无版本快照）")
    lines.append("")
    lines.append(f"--- 操作日志（最近 {len(logs)} 条） ---")
    for log in logs:
        lines.append(f"  [{log.created_at}] {log.operation_type} - {log.description}")
    lines.append("")
    lines.append("=" * 60)

    return {
        "plan_id": plan_id,
        "plan_name": plan.name,
        "versions_count": len(versions),
        "logs_count": len(logs),
        "report": "\n".join(lines),
    }
