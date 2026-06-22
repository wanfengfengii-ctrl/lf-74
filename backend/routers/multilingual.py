from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from ..models import (
    MultilingualTranscription,
    MultilingualTranscriptionCreate,
    MultilingualTranscriptionUpdate,
    AlignmentPair,
    AlignmentPairCreate,
    AlignmentPairUpdate,
    VariantAnnotation,
    VariantAnnotationCreate,
    VariantAnnotationUpdate,
    TerminologyEntry,
    TerminologyEntryCreate,
    TerminologyEntryUpdate,
    RecognitionSuggestion,
    RecognitionSuggestionCreate,
    RecognitionSuggestionUpdate,
    LeafMultilingualSummary,
    ComparativeReadingView,
)
from ..storage import (
    load_all_leaves,
    load_transcriptions_by_leaf,
    get_transcription,
    save_transcription,
    delete_transcription,
    load_alignments_by_leaf,
    get_alignment,
    save_alignment,
    delete_alignment,
    load_variants_by_leaf,
    get_variant,
    save_variant,
    delete_variant,
    load_all_terminology,
    get_terminology_entry,
    save_terminology_entry,
    delete_terminology_entry,
    load_suggestions_by_leaf,
    get_suggestion,
    save_suggestion,
    delete_suggestion,
    add_operation_log,
    get_annotation,
    load_all_plans,
    load_all_collab_projects,
    load_consensus_versions_by_project,
)

router = APIRouter(prefix="/multilingual", tags=["多语言残文识别与对读"])


LANGUAGE_OPTIONS = [
    {"code": "sa", "label": "梵文", "scripts": ["devanagari", "romanized"]},
    {"code": "pi", "label": "巴利文", "scripts": ["sinhala", "romanized"]},
    {"code": "bo", "label": "藏文", "scripts": ["tibetan", "romanized"]},
    {"code": "zh", "label": "汉文", "scripts": ["chinese"]},
    {"code": "other", "label": "其他", "scripts": ["romanized"]},
]

VARIANT_TYPES = [
    {"code": "substitution", "label": "替换"},
    {"code": "omission", "label": "缺文"},
    {"code": "addition", "label": "增文"},
    {"code": "transposition", "label": "倒文"},
    {"code": "corruption", "label": "讹误"},
]

TERMINOLOGY_CATEGORIES = [
    {"code": "doctrine", "label": "教义"},
    {"code": "ritual", "label": "仪轨"},
    {"code": "philosophy", "label": "哲学"},
    {"code": "grammar", "label": "文法"},
    {"code": "other", "label": "其他"},
]


@router.get("/languages", response_model=List[Dict[str, Any]])
def get_language_options():
    return LANGUAGE_OPTIONS


@router.get("/variant-types", response_model=List[Dict[str, Any]])
def get_variant_types():
    return VARIANT_TYPES


@router.get("/terminology-categories", response_model=List[Dict[str, Any]])
def get_terminology_categories():
    return TERMINOLOGY_CATEGORIES


@router.get("/leaves/{leaf_id}/summary", response_model=LeafMultilingualSummary)
def get_leaf_multilingual_summary(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    transcriptions = load_transcriptions_by_leaf(leaf_id)
    alignments = load_alignments_by_leaf(leaf_id)
    variants = load_variants_by_leaf(leaf_id)
    suggestions = load_suggestions_by_leaf(leaf_id)
    all_terms = load_all_terminology()

    transcription_texts = " ".join([t.full_text for t in transcriptions if t.full_text])
    matched_terms = []
    for tid, term in all_terms.items():
        if term.term and term.term in transcription_texts:
            matched_terms.append(term)

    languages = list(set([t.language for t in transcriptions]))
    pending_suggestions = len([s for s in suggestions if s.is_accepted is None])

    return LeafMultilingualSummary(
        leaf_id=leaf_id,
        transcriptions=transcriptions,
        languages=languages,
        alignment_count=len(alignments),
        variant_count=len(variants),
        suggestion_count=len(suggestions),
        pending_suggestions=pending_suggestions,
        terminology_count=len(matched_terms),
    )


@router.get("/leaves/{leaf_id}/transcriptions", response_model=List[MultilingualTranscription])
def list_leaf_transcriptions(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")
    return load_transcriptions_by_leaf(leaf_id)


@router.post("/leaves/{leaf_id}/transcriptions", response_model=MultilingualTranscription)
def create_transcription(leaf_id: str, data: MultilingualTranscriptionCreate):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    try:
        transcription = MultilingualTranscription(
            leaf_id=leaf_id,
            **data.model_dump(exclude_unset=True),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)

    saved = save_transcription(transcription)
    add_operation_log(
        operation_type="create",
        target_type="transcription",
        target_id=saved.id or leaf_id,
        description=f"为叶片 '{leaf_id}' 创建 {data.language_label or data.language} 转写",
        after_data=saved.model_dump(mode="json"),
    )
    return saved


@router.get("/transcriptions/{transcription_id}", response_model=MultilingualTranscription)
def get_transcription_detail(transcription_id: str):
    t = get_transcription(transcription_id)
    if not t:
        raise HTTPException(status_code=404, detail="转写记录不存在")
    return t


@router.put("/transcriptions/{transcription_id}", response_model=MultilingualTranscription)
def update_transcription(transcription_id: str, data: MultilingualTranscriptionUpdate):
    existing = get_transcription(transcription_id)
    if not existing:
        raise HTTPException(status_code=404, detail="转写记录不存在")

    before_data = existing.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)
    existing.updated_at = datetime.now()

    saved = save_transcription(existing)
    add_operation_log(
        operation_type="update",
        target_type="transcription",
        target_id=transcription_id,
        description=f"更新转写记录",
        before_data=before_data,
        after_data=saved.model_dump(mode="json"),
    )
    return saved


@router.delete("/transcriptions/{transcription_id}")
def delete_transcription_api(transcription_id: str):
    existing = get_transcription(transcription_id)
    if not existing:
        raise HTTPException(status_code=404, detail="转写记录不存在")

    before_data = existing.model_dump(mode="json")
    delete_transcription(transcription_id)
    add_operation_log(
        operation_type="delete",
        target_type="transcription",
        target_id=transcription_id,
        description=f"删除转写记录",
        before_data=before_data,
    )
    return {"message": "转写记录已删除"}


@router.get("/leaves/{leaf_id}/alignments", response_model=List[AlignmentPair])
def list_leaf_alignments(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")
    return load_alignments_by_leaf(leaf_id)


@router.post("/leaves/{leaf_id}/alignments", response_model=AlignmentPair)
def create_alignment(leaf_id: str, data: AlignmentPairCreate):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    try:
        alignment = AlignmentPair(
            leaf_id=leaf_id,
            **data.model_dump(exclude_unset=True),
            created_at=datetime.now(),
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)

    saved = save_alignment(alignment)
    add_operation_log(
        operation_type="create",
        target_type="alignment",
        target_id=saved.id or leaf_id,
        description=f"为叶片 '{leaf_id}' 创建 {data.source_lang}→{data.target_lang} 对齐",
        after_data=saved.model_dump(mode="json"),
    )
    return saved


@router.put("/alignments/{alignment_id}", response_model=AlignmentPair)
def update_alignment(alignment_id: str, data: AlignmentPairUpdate):
    existing = get_alignment(alignment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="对齐记录不存在")

    before_data = existing.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)

    saved = save_alignment(existing)
    add_operation_log(
        operation_type="update",
        target_type="alignment",
        target_id=alignment_id,
        description="更新对齐记录",
        before_data=before_data,
        after_data=saved.model_dump(mode="json"),
    )
    return saved


@router.delete("/alignments/{alignment_id}")
def delete_alignment_api(alignment_id: str):
    existing = get_alignment(alignment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="对齐记录不存在")

    before_data = existing.model_dump(mode="json")
    delete_alignment(alignment_id)
    add_operation_log(
        operation_type="delete",
        target_type="alignment",
        target_id=alignment_id,
        description="删除对齐记录",
        before_data=before_data,
    )
    return {"message": "对齐记录已删除"}


@router.get("/leaves/{leaf_id}/variants", response_model=List[VariantAnnotation])
def list_leaf_variants(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")
    return load_variants_by_leaf(leaf_id)


@router.post("/leaves/{leaf_id}/variants", response_model=VariantAnnotation)
def create_variant(leaf_id: str, data: VariantAnnotationCreate):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    try:
        variant = VariantAnnotation(
            leaf_id=leaf_id,
            **data.model_dump(exclude_unset=True),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)

    saved = save_variant(variant)
    add_operation_log(
        operation_type="create",
        target_type="variant",
        target_id=saved.id or leaf_id,
        description=f"为叶片 '{leaf_id}' 创建异文标注",
        after_data=saved.model_dump(mode="json"),
    )
    return saved


@router.put("/variants/{variant_id}", response_model=VariantAnnotation)
def update_variant(variant_id: str, data: VariantAnnotationUpdate):
    existing = get_variant(variant_id)
    if not existing:
        raise HTTPException(status_code=404, detail="异文记录不存在")

    before_data = existing.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)
    existing.updated_at = datetime.now()

    saved = save_variant(existing)
    add_operation_log(
        operation_type="update",
        target_type="variant",
        target_id=variant_id,
        description="更新异文记录",
        before_data=before_data,
        after_data=saved.model_dump(mode="json"),
    )
    return saved


@router.delete("/variants/{variant_id}")
def delete_variant_api(variant_id: str):
    existing = get_variant(variant_id)
    if not existing:
        raise HTTPException(status_code=404, detail="异文记录不存在")

    before_data = existing.model_dump(mode="json")
    delete_variant(variant_id)
    add_operation_log(
        operation_type="delete",
        target_type="variant",
        target_id=variant_id,
        description="删除异文记录",
        before_data=before_data,
    )
    return {"message": "异文记录已删除"}


@router.get("/terminology", response_model=List[TerminologyEntry])
def list_terminology(category: Optional[str] = None, keyword: Optional[str] = None):
    terms_dict = load_all_terminology()
    terms = list(terms_dict.values())

    if category:
        terms = [t for t in terms if t.category == category]
    if keyword:
        kw = keyword.lower()
        terms = [
            t for t in terms
            if kw in t.term.lower()
            or any(kw in v.lower() for v in t.translations.values())
            or kw in t.definition.lower()
        ]

    terms.sort(key=lambda t: t.term)
    return terms


@router.post("/terminology", response_model=TerminologyEntry)
def create_terminology(data: TerminologyEntryCreate):
    try:
        entry = TerminologyEntry(
            **data.model_dump(exclude_unset=True),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)

    saved = save_terminology_entry(entry)
    add_operation_log(
        operation_type="create",
        target_type="terminology",
        target_id=saved.id or "",
        description=f"创建术语条目: {data.term}",
        after_data=saved.model_dump(mode="json"),
    )
    return saved


@router.get("/terminology/{entry_id}", response_model=TerminologyEntry)
def get_terminology(entry_id: str):
    entry = get_terminology_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="术语条目不存在")
    return entry


@router.put("/terminology/{entry_id}", response_model=TerminologyEntry)
def update_terminology(entry_id: str, data: TerminologyEntryUpdate):
    existing = get_terminology_entry(entry_id)
    if not existing:
        raise HTTPException(status_code=404, detail="术语条目不存在")

    before_data = existing.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)
    existing.updated_at = datetime.now()

    saved = save_terminology_entry(existing)
    add_operation_log(
        operation_type="update",
        target_type="terminology",
        target_id=entry_id,
        description="更新术语条目",
        before_data=before_data,
        after_data=saved.model_dump(mode="json"),
    )
    return saved


@router.delete("/terminology/{entry_id}")
def delete_terminology_api(entry_id: str):
    existing = get_terminology_entry(entry_id)
    if not existing:
        raise HTTPException(status_code=404, detail="术语条目不存在")

    before_data = existing.model_dump(mode="json")
    delete_terminology_entry(entry_id)
    add_operation_log(
        operation_type="delete",
        target_type="terminology",
        target_id=entry_id,
        description="删除术语条目",
        before_data=before_data,
    )
    return {"message": "术语条目已删除"}


@router.get("/leaves/{leaf_id}/suggestions", response_model=List[RecognitionSuggestion])
def list_leaf_suggestions(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")
    return load_suggestions_by_leaf(leaf_id)


@router.post("/leaves/{leaf_id}/suggestions", response_model=RecognitionSuggestion)
def create_suggestion(leaf_id: str, data: RecognitionSuggestionCreate):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    try:
        suggestion = RecognitionSuggestion(
            leaf_id=leaf_id,
            **data.model_dump(exclude_unset=True),
            created_at=datetime.now(),
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)

    saved = save_suggestion(suggestion)
    add_operation_log(
        operation_type="create",
        target_type="suggestion",
        target_id=saved.id or leaf_id,
        description=f"为叶片 '{leaf_id}' 创建识别建议",
        after_data=saved.model_dump(mode="json"),
    )
    return saved


@router.put("/suggestions/{suggestion_id}", response_model=RecognitionSuggestion)
def update_suggestion(suggestion_id: str, data: RecognitionSuggestionUpdate):
    existing = get_suggestion(suggestion_id)
    if not existing:
        raise HTTPException(status_code=404, detail="建议记录不存在")

    before_data = existing.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)

    saved = save_suggestion(existing)
    action = "采纳" if data.is_accepted is True else ("驳回" if data.is_accepted is False else "更新")
    add_operation_log(
        operation_type="update",
        target_type="suggestion",
        target_id=suggestion_id,
        description=f"{action}识别建议",
        before_data=before_data,
        after_data=saved.model_dump(mode="json"),
    )
    return saved


@router.delete("/suggestions/{suggestion_id}")
def delete_suggestion_api(suggestion_id: str):
    existing = get_suggestion(suggestion_id)
    if not existing:
        raise HTTPException(status_code=404, detail="建议记录不存在")

    before_data = existing.model_dump(mode="json")
    delete_suggestion(suggestion_id)
    add_operation_log(
        operation_type="delete",
        target_type="suggestion",
        target_id=suggestion_id,
        description="删除识别建议",
        before_data=before_data,
    )
    return {"message": "建议记录已删除"}


@router.post("/leaves/{leaf_id}/auto-suggestions", response_model=List[RecognitionSuggestion])
def generate_auto_suggestions(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    annotation = get_annotation(leaf_id)
    transcriptions = load_transcriptions_by_leaf(leaf_id)
    existing_suggestions = load_suggestions_by_leaf(leaf_id)
    all_terms = load_all_terminology()

    suggestions = []

    if annotation and annotation.text_regions:
        for region in annotation.text_regions:
            region_text = region.text.strip() if region.text else ""
            if not region_text:
                continue

            for lang_info in LANGUAGE_OPTIONS:
                lang = lang_info["code"]
                has_lang = any(t.language == lang for t in transcriptions)
                if not has_lang:
                    continue

                for tid, term in all_terms.items():
                    if term.language == lang and term.term and term.term in region_text:
                        existing = any(
                            s.region_id == region.id
                            and s.suggested_text == term.term
                            and s.language == lang
                            for s in existing_suggestions
                        )
                        if not existing:
                            suggestion = RecognitionSuggestion(
                                leaf_id=leaf_id,
                                language=lang,
                                region_id=region.id,
                                suggested_text=term.term,
                                confidence=0.75,
                                method="dictionary",
                                explanation=f"匹配术语词典中的 '{term.term}'（{lang_info['label']}）",
                                alternatives=[
                                    {"text": trans, "confidence": 0.6}
                                    for trans in list(term.translations.values())[:3]
                                ],
                                created_at=datetime.now(),
                            )
                            saved = save_suggestion(suggestion)
                            suggestions.append(saved)

    return suggestions


@router.get("/leaves/{leaf_id}/comparative-view", response_model=ComparativeReadingView)
def get_comparative_reading_view(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")

    leaf = leaves[leaf_id]
    transcriptions = load_transcriptions_by_leaf(leaf_id)
    alignments = load_alignments_by_leaf(leaf_id)
    variants = load_variants_by_leaf(leaf_id)
    suggestions = load_suggestions_by_leaf(leaf_id)

    transcriptions_by_lang: Dict[str, MultilingualTranscription] = {}
    for t in transcriptions:
        transcriptions_by_lang[t.language] = t

    all_terms = load_all_terminology()
    transcription_texts = " ".join([t.full_text for t in transcriptions if t.full_text])
    matched_terms = []
    for tid, term in all_terms.items():
        if term.term and term.term in transcription_texts:
            matched_terms.append(term)

    plans = load_all_plans()
    plan_info = None
    for plan_id, plan in plans.items():
        plan_leaf_ids = [l.leaf_id for l in plan.leaves]
        if leaf_id in plan_leaf_ids:
            leaf_in_plan = next((l for l in plan.leaves if l.leaf_id == leaf_id), None)
            plan_info = {
                "plan_id": plan.id,
                "plan_name": plan.name,
                "is_final": plan.is_final,
                "order": leaf_in_plan.order if leaf_in_plan else None,
                "flipped": leaf_in_plan.flipped if leaf_in_plan else False,
            }
            break

    annotation = get_annotation(leaf_id)
    annotation_info = None
    if annotation:
        annotation_info = {
            "image_path": annotation.image_path,
            "hole_count": len(annotation.holes),
            "damage_count": len(annotation.damage_regions),
            "text_region_count": len(annotation.text_regions),
            "text_regions": [
                {"id": tr.id, "text": tr.text, "x": tr.x, "y": tr.y, "width": tr.width, "height": tr.height}
                for tr in annotation.text_regions
            ],
        }

    projects = load_all_collab_projects()
    consensus_info = None
    for pid, project in projects.items():
        if leaf_id in project.target_leaf_ids:
            versions = load_consensus_versions_by_project(pid)
            if versions:
                latest = versions[0]
                leaf_in_consensus = next((l for l in latest.ordered_leaves if l.leaf_id == leaf_id), None)
                consensus_info = {
                    "project_id": pid,
                    "project_name": project.name,
                    "version": latest.version,
                    "version_name": latest.name,
                    "is_final": latest.is_final,
                    "consensus_note": latest.consensus_notes.get(leaf_id, ""),
                    "order": leaf_in_consensus.order if leaf_in_consensus else None,
                    "flipped": leaf_in_consensus.flipped if leaf_in_consensus else False,
                }
                break

    return ComparativeReadingView(
        leaf_id=leaf_id,
        leaf_info=leaf.model_dump(mode="json"),
        transcriptions_by_lang=transcriptions_by_lang,
        alignments=alignments,
        variants=variants,
        terminology=matched_terms,
        suggestions=suggestions,
        plan_info=plan_info,
        annotation_info=annotation_info,
        consensus_info=consensus_info,
    )
