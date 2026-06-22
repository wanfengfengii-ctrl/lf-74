import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import ValidationError

from ..models import (
    LeafAnnotation,
    LeafAnnotationUpdate,
    OperationType,
    ImageHole,
    DamageRegion,
    TextRegion,
    HolePosition,
)
from ..storage import (
    load_all_leaves,
    save_all_leaves,
    get_annotation,
    save_annotation,
    delete_annotation,
    save_image_file,
    get_image_path,
    add_operation_log,
    load_all_plans,
    save_all_plans,
)
from ..sorting import evaluate_plan

router = APIRouter(prefix="/annotations", tags=["叶片图片标注"])


@router.get("/{leaf_id}", response_model=Optional[LeafAnnotation])
def get_leaf_annotation(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")
    return get_annotation(leaf_id)


@router.put("/{leaf_id}", response_model=LeafAnnotation)
def update_leaf_annotation(leaf_id: str, data: LeafAnnotationUpdate):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    existing = get_annotation(leaf_id)
    before_data = existing.model_dump(mode="json") if existing else None

    if existing:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "holes" and value is not None:
                value = [ImageHole(**h) if isinstance(h, dict) else h for h in value]
            elif field == "damage_regions" and value is not None:
                value = [DamageRegion(**d) if isinstance(d, dict) else d for d in value]
            elif field == "text_regions" and value is not None:
                value = [TextRegion(**t) if isinstance(t, dict) else t for t in value]
            setattr(existing, field, value)
        existing.updated_at = datetime.now()
        annotation = existing
    else:
        try:
            annotation = LeafAnnotation(
                leaf_id=leaf_id,
                **data.model_dump(exclude_unset=True),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        except ValidationError as e:
            detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
            raise HTTPException(status_code=400, detail=detail)

    save_annotation(annotation)

    update_data = data.model_dump(exclude_unset=True)
    leaf = leaves[leaf_id]
    leaf_changed = False

    if "holes" in update_data:
        real_holes = []
        for h in annotation.holes:
            h_obj = ImageHole(**h) if isinstance(h, dict) else h
            if h_obj.real_x is not None and h_obj.real_y is not None:
                real_holes.append(HolePosition(x=h_obj.real_x, y=h_obj.real_y))
        if real_holes != leaf.holes:
            leaf.holes = real_holes
            leaf_changed = True

    if "text_regions" in update_data:
        combined_text = " ".join(
            [(TextRegion(**tr).text if isinstance(tr, dict) else tr.text)
             for tr in annotation.text_regions
             if (TextRegion(**tr).text if isinstance(tr, dict) else tr.text).strip()]
        )
        if combined_text != leaf.residual_text:
            leaf.residual_text = combined_text
            leaf_changed = True

    if "damage_regions" in update_data:
        damage_desc = "; ".join(
            [f"{(DamageRegion(**dr).severity if isinstance(dr, dict) else dr.severity)}: "
             f"{(DamageRegion(**dr).description if isinstance(dr, dict) else dr.description)}"
             for dr in annotation.damage_regions
             if (DamageRegion(**dr).description if isinstance(dr, dict) else dr.description).strip()]
        )
        if damage_desc != leaf.damage:
            leaf.damage = damage_desc
            leaf_changed = True

    if leaf_changed:
        leaf.updated_at = datetime.now()
        leaves[leaf_id] = leaf
        save_all_leaves(leaves)

        plans = load_all_plans()
        plans_changed = False
        for plan_id, plan in plans.items():
            plan_leaf_ids = [l.leaf_id for l in plan.leaves]
            if leaf_id in plan_leaf_ids:
                old_score = plan.score
                plan.score = evaluate_plan(plan.leaves, leaves)
                plan.updated_at = datetime.now()
                plans[plan_id] = plan
                plans_changed = True
                if old_score != plan.score:
                    add_operation_log(
                        operation_type=OperationType.UPDATE,
                        target_type="plan",
                        target_id=plan_id,
                        description=f"叶片 '{leaf_id}' 标注变化导致方案评分更新: {old_score} -> {plan.score}",
                    )
        if plans_changed:
            save_all_plans(plans)

    add_operation_log(
        operation_type=OperationType.UPDATE,
        target_type="annotation",
        target_id=leaf_id,
        description=f"更新叶片 '{leaf_id}' 的图片标注",
        before_data=before_data,
        after_data=annotation.model_dump(mode="json"),
    )

    return annotation


@router.post("/{leaf_id}/upload-image")
def upload_leaf_image(leaf_id: str, file: UploadFile = File(...)):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    content = file.file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 20MB")

    relative_path = save_image_file(leaf_id, file.filename or "image.png", content)

    leaf = leaves[leaf_id]
    old_image_path = leaf.image_path
    leaf.image_path = relative_path
    leaf.updated_at = datetime.now()
    leaves[leaf_id] = leaf
    save_all_leaves(leaves)

    existing = get_annotation(leaf_id)
    if existing:
        existing.image_path = relative_path
        existing.updated_at = datetime.now()
        save_annotation(existing)
    else:
        from ..models import LeafAnnotation
        annotation = LeafAnnotation(
            leaf_id=leaf_id,
            image_path=relative_path,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        save_annotation(annotation)

    add_operation_log(
        operation_type=OperationType.UPLOAD,
        target_type="annotation",
        target_id=leaf_id,
        description=f"上传叶片 '{leaf_id}' 的高清图片: {file.filename}",
        before_data={"image_path": old_image_path},
        after_data={"image_path": relative_path},
    )

    return {
        "message": "图片上传成功",
        "image_path": relative_path,
        "image_url": f"/api/annotations/{leaf_id}/image",
    }


@router.get("/{leaf_id}/image")
def get_leaf_image(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    leaf = leaves[leaf_id]
    if not leaf.image_path:
        annotation = get_annotation(leaf_id)
        if annotation and annotation.image_path:
            leaf.image_path = annotation.image_path
        else:
            raise HTTPException(status_code=404, detail="该叶片暂无图片")

    full_path = get_image_path(leaf.image_path)
    if not full_path:
        raise HTTPException(status_code=404, detail="图片文件不存在")

    ext = os.path.splitext(full_path)[1].lower()
    media_type = "image/png"
    if ext in (".jpg", ".jpeg"):
        media_type = "image/jpeg"
    elif ext == ".gif":
        media_type = "image/gif"
    elif ext == ".webp":
        media_type = "image/webp"

    return FileResponse(full_path, media_type=media_type)


@router.delete("/{leaf_id}")
def delete_leaf_annotation(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    existing = get_annotation(leaf_id)
    if not existing:
        raise HTTPException(status_code=404, detail="该叶片暂无标注数据")

    before_data = existing.model_dump(mode="json")
    delete_annotation(leaf_id)

    add_operation_log(
        operation_type=OperationType.DELETE,
        target_type="annotation",
        target_id=leaf_id,
        description=f"删除叶片 '{leaf_id}' 的标注数据",
        before_data=before_data,
    )

    return {"message": f"叶片 '{leaf_id}' 的标注数据已删除"}
