from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from ..models import Leaf, LeafCreate, LeafUpdate, OperationType
from ..storage import (
    load_all_leaves, save_all_leaves, add_operation_log, delete_annotation,
    load_all_plans, save_all_plans,
    load_all_collab_projects, save_all_collab_projects,
    load_all_submissions, save_all_submissions,
    load_all_discussions, save_all_discussions,
    load_all_consensus_versions, save_all_consensus_versions,
)
from ..sorting import evaluate_plan

router = APIRouter(prefix="/leaves", tags=["叶片管理"])


@router.get("", response_model=List[Leaf])
def list_leaves():
    leaves = load_all_leaves()
    return sorted(leaves.values(), key=lambda l: l.id)


@router.get("/{leaf_id}", response_model=Leaf)
def get_leaf(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")
    return leaves[leaf_id]


@router.post("", response_model=Leaf)
def create_leaf(leaf_data: LeafCreate):
    leaves = load_all_leaves()
    if leaf_data.id in leaves:
        raise HTTPException(status_code=400, detail=f"叶片编号 '{leaf_data.id}' 已存在，不能重复")

    now = datetime.now()
    try:
        leaf = Leaf(
            **leaf_data.model_dump(),
            created_at=now,
            updated_at=now,
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)

    leaves[leaf.id] = leaf
    save_all_leaves(leaves)

    add_operation_log(
        operation_type=OperationType.CREATE,
        target_type="leaf",
        target_id=leaf.id,
        description=f"创建叶片 '{leaf.id}'",
        after_data=leaf.model_dump(mode="json"),
    )

    return leaf


@router.put("/{leaf_id}", response_model=Leaf)
def update_leaf(leaf_id: str, leaf_data: LeafUpdate):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    existing = leaves[leaf_id]
    before_data = existing.model_dump(mode="json")
    update_data = leaf_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(existing, field, value)

    existing.updated_at = datetime.now()

    try:
        existing = Leaf.model_validate(existing.model_dump())
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)

    leaves[leaf_id] = existing
    save_all_leaves(leaves)

    changed_fields = list(update_data.keys())
    op_type = OperationType.CONFIRM if "confirmed" in changed_fields and existing.confirmed else OperationType.UPDATE
    add_operation_log(
        operation_type=op_type,
        target_type="leaf",
        target_id=leaf_id,
        description=f"更新叶片 '{leaf_id}'，修改字段: {', '.join(changed_fields)}",
        before_data=before_data,
        after_data=existing.model_dump(mode="json"),
    )

    return existing


@router.delete("/{leaf_id}")
def delete_leaf(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    before_data = leaves[leaf_id].model_dump(mode="json")
    del leaves[leaf_id]
    save_all_leaves(leaves)
    delete_annotation(leaf_id)

    plans = load_all_plans()
    plans_changed = False
    affected_plans = []
    for plan_id, plan in plans.items():
        plan_leaf_ids = [l.leaf_id for l in plan.leaves]
        if leaf_id in plan_leaf_ids:
            plan.leaves = [l for l in plan.leaves if l.leaf_id != leaf_id]
            for i, l in enumerate(plan.leaves):
                l.order = i
            plan.score = evaluate_plan(plan.leaves, leaves)
            plan.updated_at = datetime.now()
            plans[plan_id] = plan
            plans_changed = True
            affected_plans.append(plan_id)
    if plans_changed:
        save_all_plans(plans)

    collab_notes = []

    collab_projects = load_all_collab_projects()
    collab_projects_changed = False
    affected_projects = []
    for pid, proj in collab_projects.items():
        if leaf_id in proj.target_leaf_ids:
            proj.target_leaf_ids = [lid for lid in proj.target_leaf_ids if lid != leaf_id]
            proj.updated_at = datetime.now()
            collab_projects[pid] = proj
            collab_projects_changed = True
            affected_projects.append(pid)
    if collab_projects_changed:
        save_all_collab_projects(collab_projects)
        collab_notes.append(f"已从 {len(affected_projects)} 个协同项目中移除")

    all_submissions = load_all_submissions()
    subs_changed = False
    affected_submissions = 0
    for idx, sub in enumerate(all_submissions):
        changed = False
        if any(rl.leaf_id == leaf_id for rl in sub.ordered_leaves):
            sub.ordered_leaves = [rl for rl in sub.ordered_leaves if rl.leaf_id != leaf_id]
            changed = True
        if any(op.leaf_id == leaf_id for op in sub.annotation_opinions):
            sub.annotation_opinions = [op for op in sub.annotation_opinions if op.leaf_id != leaf_id]
            changed = True
        if any(note.leaf_id == leaf_id for note in sub.dispute_notes):
            sub.dispute_notes = [note for note in sub.dispute_notes if note.leaf_id != leaf_id]
            changed = True
        if changed:
            all_submissions[idx] = sub
            subs_changed = True
            affected_submissions += 1
    if subs_changed:
        save_all_submissions(all_submissions)
        collab_notes.append(f"已清理 {affected_submissions} 份提交记录中的相关内容")

    all_discussions = load_all_discussions()
    discs_changed = False
    affected_discs = 0
    for idx, msg in enumerate(all_discussions):
        changed = False
        if msg.leaf_id == leaf_id:
            msg.leaf_id = None
            changed = True
        if msg.tags and leaf_id in msg.tags:
            msg.tags = [t for t in msg.tags if t != leaf_id]
            changed = True
        if changed:
            all_discussions[idx] = msg
            discs_changed = True
            affected_discs += 1
    if discs_changed:
        save_all_discussions(all_discussions)
        collab_notes.append(f"已解除 {affected_discs} 条讨论对该叶片的关联")

    all_versions = load_all_consensus_versions()
    vers_changed = False
    affected_vers = 0
    for idx, ver in enumerate(all_versions):
        changed = False
        if any(rl.leaf_id == leaf_id for rl in ver.ordered_leaves):
            ver.ordered_leaves = [rl for rl in ver.ordered_leaves if rl.leaf_id != leaf_id]
            changed = True
        if leaf_id in (ver.consensus_notes or {}):
            new_notes = dict(ver.consensus_notes or {})
            del new_notes[leaf_id]
            ver.consensus_notes = new_notes
            changed = True
        if leaf_id in (ver.unresolved_disputes or []):
            ver.unresolved_disputes = [rid for rid in (ver.unresolved_disputes or []) if rid != leaf_id]
            changed = True
        if changed:
            all_versions[idx] = ver
            vers_changed = True
            affected_vers += 1
    if vers_changed:
        save_all_consensus_versions(all_versions)
        collab_notes.append(f"已清理 {affected_vers} 个共识版本中的相关内容")

    extra_desc = ""
    if affected_plans:
        extra_desc += f"，已从 {len(affected_plans)} 个方案中移除"
    if collab_notes:
        extra_desc += "；" + "；".join(collab_notes)

    add_operation_log(
        operation_type=OperationType.DELETE,
        target_type="leaf",
        target_id=leaf_id,
        description=f"删除叶片 '{leaf_id}'" + extra_desc,
        before_data=before_data,
    )

    return {
        "message": f"叶片 '{leaf_id}' 已删除",
        "removed_from_plans": affected_plans,
        "removed_from_projects": affected_projects,
        "cleaned_submissions": affected_submissions,
        "cleaned_discussions": affected_discs,
        "cleaned_consensus_versions": affected_vers,
    }
