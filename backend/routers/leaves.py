from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from ..models import Leaf, LeafCreate, LeafUpdate, OperationType
from ..storage import load_all_leaves, save_all_leaves, add_operation_log, delete_annotation

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

    add_operation_log(
        operation_type=OperationType.DELETE,
        target_type="leaf",
        target_id=leaf_id,
        description=f"删除叶片 '{leaf_id}'",
        before_data=before_data,
    )

    return {"message": f"叶片 '{leaf_id}' 已删除"}
