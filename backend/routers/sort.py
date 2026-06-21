from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..models import SortRecommendation, SortResult
from ..sorting import recommend_next_leaf, sort_all_leaves
from ..storage import load_all_leaves

router = APIRouter(prefix="/sort", tags=["排序推荐"])


@router.get("/next/{current_leaf_id}", response_model=List[SortRecommendation])
def get_next_leaf_recommendations(
    current_leaf_id: str,
    hole_weight: float = Query(0.5, ge=0.0, le=1.0),
    text_weight: float = Query(0.5, ge=0.0, le=1.0),
    exclude_ids: Optional[str] = Query(None, description="已排除的叶片编号，逗号分隔"),
):
    leaves = load_all_leaves()
    if current_leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{current_leaf_id}' 不存在")

    current_leaf = leaves[current_leaf_id]

    excluded = set()
    if exclude_ids:
        excluded = {eid.strip() for eid in exclude_ids.split(",") if eid.strip()}

    candidates = [leaf for lid, leaf in leaves.items() if lid not in excluded]

    return recommend_next_leaf(current_leaf, candidates, hole_weight, text_weight)


@router.get("/all", response_model=SortResult)
def get_full_sort_recommendation(
    start_leaf_id: Optional[str] = None,
    hole_weight: float = Query(0.5, ge=0.0, le=1.0),
    text_weight: float = Query(0.5, ge=0.0, le=1.0),
):
    leaves = load_all_leaves()
    if not leaves:
        raise HTTPException(status_code=400, detail="没有可排序的叶片")

    if start_leaf_id and start_leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"起始叶片 '{start_leaf_id}' 不存在")

    return sort_all_leaves(leaves, start_leaf_id, hole_weight, text_weight)
