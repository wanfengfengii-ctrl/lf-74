import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from ..models import (
    DiscoverySite,
    DiscoverySiteCreate,
    DiscoverySiteUpdate,
    CollectionUnit,
    CollectionUnitCreate,
    CollectionUnitUpdate,
    ProvenanceTransfer,
    ProvenanceTransferCreate,
    ProvenanceTransferUpdate,
    RepairRecord,
    RepairRecordCreate,
    RepairRecordUpdate,
    ResearchCitation,
    ResearchCitationCreate,
    ResearchCitationUpdate,
    TimelineEvent,
    ProvenanceTimeline,
    GraphNode,
    GraphEdge,
    ProvenanceGraph,
    LeafProvenanceSummary,
    RelatedLeafInfo,
    OperationType,
)
from ..storage import (
    load_all_leaves,
    add_operation_log,
    load_all_discovery_sites,
    save_all_discovery_sites,
    get_discovery_site,
    get_leaf_discovery_site_id,
    set_leaf_discovery_site,
    get_leaves_by_discovery_site,
    load_all_collection_units,
    save_all_collection_units,
    get_collection_unit,
    load_transfers_by_leaf,
    get_provenance_transfer,
    save_provenance_transfer,
    delete_provenance_transfer,
    load_repairs_by_leaf,
    get_repair_record,
    save_repair_record,
    delete_repair_record,
    load_citations_by_leaf,
    get_research_citation,
    save_research_citation,
    delete_research_citation,
    get_leaf_current_unit,
    load_all_plans,
    load_all_collab_projects,
    get_annotation,
    load_all_provenance_transfers,
    load_all_repair_records,
    load_all_research_citations,
    load_all_consensus_versions,
    load_consensus_versions_by_project,
)

router = APIRouter(prefix="/provenance", tags=["叶片谱系与来源流转"])


def _validate_leaf_exists(leaf_id: str):
    leaves = load_all_leaves()
    if leaf_id not in leaves:
        raise HTTPException(status_code=404, detail=f"叶片 '{leaf_id}' 不存在")


@router.get("/sites", response_model=List[DiscoverySite])
def list_discovery_sites():
    sites = load_all_discovery_sites()
    return sorted(sites.values(), key=lambda s: s.created_at, reverse=True)


@router.get("/sites/{site_id}", response_model=DiscoverySite)
def get_discovery_site_detail(site_id: str):
    site = get_discovery_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"发现地点 '{site_id}' 不存在")
    return site


@router.get("/sites/{site_id}/leaves", response_model=List[str])
def list_leaves_by_site(site_id: str):
    site = get_discovery_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"发现地点 '{site_id}' 不存在")
    return get_leaves_by_discovery_site(site_id)


@router.post("/sites", response_model=DiscoverySite)
def create_discovery_site(data: DiscoverySiteCreate):
    sites = load_all_discovery_sites()
    if data.id in sites:
        raise HTTPException(status_code=400, detail=f"发现地点编号 '{data.id}' 已存在")
    now = datetime.now()
    try:
        site = DiscoverySite(**data.model_dump(), created_at=now, updated_at=now)
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    sites[site.id] = site
    save_all_discovery_sites(sites)
    add_operation_log(
        operation_type=OperationType.CREATE,
        target_type="discovery_site",
        target_id=site.id,
        description=f"创建发现地点 '{site.name}' ({site.id})",
        after_data=site.model_dump(mode="json"),
    )
    return site


@router.put("/sites/{site_id}", response_model=DiscoverySite)
def update_discovery_site(site_id: str, data: DiscoverySiteUpdate):
    sites = load_all_discovery_sites()
    if site_id not in sites:
        raise HTTPException(status_code=404, detail=f"发现地点 '{site_id}' 不存在")
    existing = sites[site_id]
    before_data = existing.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)
    existing.updated_at = datetime.now()
    try:
        existing = DiscoverySite.model_validate(existing.model_dump())
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    sites[site_id] = existing
    save_all_discovery_sites(sites)
    changed_fields = list(update_data.keys())
    add_operation_log(
        operation_type=OperationType.UPDATE,
        target_type="discovery_site",
        target_id=site_id,
        description=f"更新发现地点 '{existing.name}'，修改字段: {', '.join(changed_fields)}",
        before_data=before_data,
        after_data=existing.model_dump(mode="json"),
    )
    return existing


@router.delete("/sites/{site_id}")
def delete_discovery_site(site_id: str):
    sites = load_all_discovery_sites()
    if site_id not in sites:
        raise HTTPException(status_code=404, detail=f"发现地点 '{site_id}' 不存在")
    linked_leaves = get_leaves_by_discovery_site(site_id)
    if linked_leaves:
        for lid in linked_leaves:
            set_leaf_discovery_site(lid, None)
    before_data = sites[site_id].model_dump(mode="json")
    site_name = sites[site_id].name
    del sites[site_id]
    save_all_discovery_sites(sites)
    add_operation_log(
        operation_type=OperationType.DELETE,
        target_type="discovery_site",
        target_id=site_id,
        description=f"删除发现地点 '{site_name}' ({site_id})，已解除 {len(linked_leaves)} 片叶片的关联",
        before_data=before_data,
    )
    return {"message": f"发现地点 '{site_id}' 已删除", "unlinked_leaves": linked_leaves}


@router.get("/units", response_model=List[CollectionUnit])
def list_collection_units():
    units = load_all_collection_units()
    return sorted(units.values(), key=lambda u: u.created_at, reverse=True)


@router.get("/units/{unit_id}", response_model=CollectionUnit)
def get_collection_unit_detail(unit_id: str):
    unit = get_collection_unit(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail=f"收藏单位 '{unit_id}' 不存在")
    return unit


@router.post("/units", response_model=CollectionUnit)
def create_collection_unit(data: CollectionUnitCreate):
    units = load_all_collection_units()
    if data.id in units:
        raise HTTPException(status_code=400, detail=f"收藏单位编号 '{data.id}' 已存在")
    now = datetime.now()
    try:
        unit = CollectionUnit(**data.model_dump(), created_at=now, updated_at=now)
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    units[unit.id] = unit
    save_all_collection_units(units)
    add_operation_log(
        operation_type=OperationType.CREATE,
        target_type="collection_unit",
        target_id=unit.id,
        description=f"创建收藏单位 '{unit.name}' ({unit.id})",
        after_data=unit.model_dump(mode="json"),
    )
    return unit


@router.put("/units/{unit_id}", response_model=CollectionUnit)
def update_collection_unit(unit_id: str, data: CollectionUnitUpdate):
    units = load_all_collection_units()
    if unit_id not in units:
        raise HTTPException(status_code=404, detail=f"收藏单位 '{unit_id}' 不存在")
    existing = units[unit_id]
    before_data = existing.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)
    existing.updated_at = datetime.now()
    try:
        existing = CollectionUnit.model_validate(existing.model_dump())
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    units[unit_id] = existing
    save_all_collection_units(units)
    changed_fields = list(update_data.keys())
    add_operation_log(
        operation_type=OperationType.UPDATE,
        target_type="collection_unit",
        target_id=unit_id,
        description=f"更新收藏单位 '{existing.name}'，修改字段: {', '.join(changed_fields)}",
        before_data=before_data,
        after_data=existing.model_dump(mode="json"),
    )
    return existing


@router.delete("/units/{unit_id}")
def delete_collection_unit(unit_id: str):
    units = load_all_collection_units()
    if unit_id not in units:
        raise HTTPException(status_code=404, detail=f"收藏单位 '{unit_id}' 不存在")
    before_data = units[unit_id].model_dump(mode="json")
    unit_name = units[unit_id].name
    del units[unit_id]
    save_all_collection_units(units)
    add_operation_log(
        operation_type=OperationType.DELETE,
        target_type="collection_unit",
        target_id=unit_id,
        description=f"删除收藏单位 '{unit_name}' ({unit_id})",
        before_data=before_data,
    )
    return {"message": f"收藏单位 '{unit_id}' 已删除"}


@router.put("/leaves/{leaf_id}/discovery-site")
def link_leaf_to_discovery_site(leaf_id: str, site_id: Optional[str] = None):
    _validate_leaf_exists(leaf_id)
    if site_id is not None:
        site = get_discovery_site(site_id)
        if not site:
            raise HTTPException(status_code=404, detail=f"发现地点 '{site_id}' 不存在")
    set_leaf_discovery_site(leaf_id, site_id)
    action = "关联" if site_id else "解除关联"
    site_info = f"'{site_id}'" if site_id else ""
    add_operation_log(
        operation_type=OperationType.UPDATE,
        target_type="leaf",
        target_id=leaf_id,
        description=f"{action}叶片与发现地点{site_info}的关联",
    )
    return {"message": f"叶片 '{leaf_id}' 与发现地点的关联已更新", "leaf_id": leaf_id, "site_id": site_id}


@router.get("/leaves/{leaf_id}/transfers", response_model=List[ProvenanceTransfer])
def list_leaf_transfers(leaf_id: str):
    _validate_leaf_exists(leaf_id)
    return load_transfers_by_leaf(leaf_id)


@router.post("/leaves/{leaf_id}/transfers", response_model=ProvenanceTransfer)
def create_transfer(leaf_id: str, data: ProvenanceTransferCreate):
    _validate_leaf_exists(leaf_id)
    to_unit = get_collection_unit(data.to_unit_id)
    if not to_unit:
        raise HTTPException(status_code=400, detail=f"转入收藏单位 '{data.to_unit_id}' 不存在")
    if data.from_unit_id is not None:
        from_unit = get_collection_unit(data.from_unit_id)
        if not from_unit:
            raise HTTPException(status_code=400, detail=f"转出收藏单位 '{data.from_unit_id}' 不存在")
    now = datetime.now()
    try:
        transfer = ProvenanceTransfer(
            **data.model_dump(),
            leaf_id=leaf_id,
            created_at=now,
            updated_at=now,
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    transfer = save_provenance_transfer(transfer)
    add_operation_log(
        operation_type=OperationType.CREATE,
        target_type="provenance_transfer",
        target_id=transfer.id,
        description=f"为叶片 '{leaf_id}' 创建流转记录: {transfer.transfer_type}",
        after_data=transfer.model_dump(mode="json"),
    )
    return transfer


@router.get("/transfers/{transfer_id}", response_model=ProvenanceTransfer)
def get_transfer_detail(transfer_id: str):
    transfer = get_provenance_transfer(transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail=f"流转记录 '{transfer_id}' 不存在")
    return transfer


@router.put("/transfers/{transfer_id}", response_model=ProvenanceTransfer)
def update_transfer(transfer_id: str, data: ProvenanceTransferUpdate):
    existing = get_provenance_transfer(transfer_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"流转记录 '{transfer_id}' 不存在")
    before_data = existing.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)
    if "to_unit_id" in update_data:
        to_unit = get_collection_unit(update_data["to_unit_id"])
        if not to_unit:
            raise HTTPException(status_code=400, detail=f"转入收藏单位 '{update_data['to_unit_id']}' 不存在")
    if "from_unit_id" in update_data and update_data["from_unit_id"] is not None:
        from_unit = get_collection_unit(update_data["from_unit_id"])
        if not from_unit:
            raise HTTPException(status_code=400, detail=f"转出收藏单位 '{update_data['from_unit_id']}' 不存在")
    for field, value in update_data.items():
        setattr(existing, field, value)
    existing.updated_at = datetime.now()
    try:
        existing = ProvenanceTransfer.model_validate(existing.model_dump())
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    save_provenance_transfer(existing)
    changed_fields = list(update_data.keys())
    add_operation_log(
        operation_type=OperationType.UPDATE,
        target_type="provenance_transfer",
        target_id=transfer_id,
        description=f"更新流转记录，修改字段: {', '.join(changed_fields)}",
        before_data=before_data,
        after_data=existing.model_dump(mode="json"),
    )
    return existing


@router.delete("/transfers/{transfer_id}")
def delete_transfer(transfer_id: str):
    existing = get_provenance_transfer(transfer_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"流转记录 '{transfer_id}' 不存在")
    before_data = existing.model_dump(mode="json")
    leaf_id = existing.leaf_id
    delete_provenance_transfer(transfer_id)
    add_operation_log(
        operation_type=OperationType.DELETE,
        target_type="provenance_transfer",
        target_id=transfer_id,
        description=f"删除叶片 '{leaf_id}' 的流转记录",
        before_data=before_data,
    )
    return {"message": f"流转记录 '{transfer_id}' 已删除"}


@router.get("/leaves/{leaf_id}/repairs", response_model=List[RepairRecord])
def list_leaf_repairs(leaf_id: str):
    _validate_leaf_exists(leaf_id)
    return load_repairs_by_leaf(leaf_id)


@router.post("/leaves/{leaf_id}/repairs", response_model=RepairRecord)
def create_repair_record(leaf_id: str, data: RepairRecordCreate):
    _validate_leaf_exists(leaf_id)
    now = datetime.now()
    try:
        record = RepairRecord(
            **data.model_dump(),
            leaf_id=leaf_id,
            created_at=now,
            updated_at=now,
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    record = save_repair_record(record)
    add_operation_log(
        operation_type=OperationType.CREATE,
        target_type="repair_record",
        target_id=record.id,
        description=f"为叶片 '{leaf_id}' 创建修复记录: {record.repair_type}",
        after_data=record.model_dump(mode="json"),
    )
    return record


@router.get("/repairs/{record_id}", response_model=RepairRecord)
def get_repair_detail(record_id: str):
    record = get_repair_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"修复记录 '{record_id}' 不存在")
    return record


@router.put("/repairs/{record_id}", response_model=RepairRecord)
def update_repair_record(record_id: str, data: RepairRecordUpdate):
    existing = get_repair_record(record_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"修复记录 '{record_id}' 不存在")
    before_data = existing.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)
    existing.updated_at = datetime.now()
    try:
        existing = RepairRecord.model_validate(existing.model_dump())
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    save_repair_record(existing)
    changed_fields = list(update_data.keys())
    add_operation_log(
        operation_type=OperationType.UPDATE,
        target_type="repair_record",
        target_id=record_id,
        description=f"更新修复记录，修改字段: {', '.join(changed_fields)}",
        before_data=before_data,
        after_data=existing.model_dump(mode="json"),
    )
    return existing


@router.delete("/repairs/{record_id}")
def delete_repair_record_endpoint(record_id: str):
    existing = get_repair_record(record_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"修复记录 '{record_id}' 不存在")
    before_data = existing.model_dump(mode="json")
    leaf_id = existing.leaf_id
    delete_repair_record(record_id)
    add_operation_log(
        operation_type=OperationType.DELETE,
        target_type="repair_record",
        target_id=record_id,
        description=f"删除叶片 '{leaf_id}' 的修复记录",
        before_data=before_data,
    )
    return {"message": f"修复记录 '{record_id}' 已删除"}


@router.get("/leaves/{leaf_id}/citations", response_model=List[ResearchCitation])
def list_leaf_citations(leaf_id: str):
    _validate_leaf_exists(leaf_id)
    return load_citations_by_leaf(leaf_id)


@router.post("/leaves/{leaf_id}/citations", response_model=ResearchCitation)
def create_citation(leaf_id: str, data: ResearchCitationCreate):
    _validate_leaf_exists(leaf_id)
    now = datetime.now()
    try:
        citation = ResearchCitation(
            **data.model_dump(),
            leaf_id=leaf_id,
            created_at=now,
            updated_at=now,
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    citation = save_research_citation(citation)
    add_operation_log(
        operation_type=OperationType.CREATE,
        target_type="research_citation",
        target_id=citation.id,
        description=f"为叶片 '{leaf_id}' 添加学术引用: {citation.title}",
        after_data=citation.model_dump(mode="json"),
    )
    return citation


@router.get("/citations/{citation_id}", response_model=ResearchCitation)
def get_citation_detail(citation_id: str):
    citation = get_research_citation(citation_id)
    if not citation:
        raise HTTPException(status_code=404, detail=f"引用记录 '{citation_id}' 不存在")
    return citation


@router.put("/citations/{citation_id}", response_model=ResearchCitation)
def update_citation(citation_id: str, data: ResearchCitationUpdate):
    existing = get_research_citation(citation_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"引用记录 '{citation_id}' 不存在")
    before_data = existing.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)
    existing.updated_at = datetime.now()
    try:
        existing = ResearchCitation.model_validate(existing.model_dump())
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    save_research_citation(existing)
    changed_fields = list(update_data.keys())
    add_operation_log(
        operation_type=OperationType.UPDATE,
        target_type="research_citation",
        target_id=citation_id,
        description=f"更新学术引用，修改字段: {', '.join(changed_fields)}",
        before_data=before_data,
        after_data=existing.model_dump(mode="json"),
    )
    return existing


@router.delete("/citations/{citation_id}")
def delete_citation_endpoint(citation_id: str):
    existing = get_research_citation(citation_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"引用记录 '{citation_id}' 不存在")
    before_data = existing.model_dump(mode="json")
    leaf_id = existing.leaf_id
    delete_research_citation(citation_id)
    add_operation_log(
        operation_type=OperationType.DELETE,
        target_type="research_citation",
        target_id=citation_id,
        description=f"删除叶片 '{leaf_id}' 的学术引用",
        before_data=before_data,
    )
    return {"message": f"引用记录 '{citation_id}' 已删除"}


def _parse_date_sort_key(date_str: Optional[str]) -> str:
    if not date_str:
        return "9999-12-31"
    return date_str


@router.get("/leaves/{leaf_id}/timeline", response_model=ProvenanceTimeline)
def get_leaf_provenance_timeline(leaf_id: str):
    _validate_leaf_exists(leaf_id)
    leaves = load_all_leaves()
    leaf = leaves[leaf_id]
    events: List[TimelineEvent] = []

    site_id = get_leaf_discovery_site_id(leaf_id)
    if site_id:
        site = get_discovery_site(site_id)
        if site:
            events.append(TimelineEvent(
                event_id=f"discovery_{site_id}",
                event_type="discovery",
                event_date=site.discovery_date,
                title=f"于 {site.name} 发现",
                description=site.description or f"在 {site.region} {site.name} 发现",
                location=site.name,
                related_entity_id=site_id,
                related_entity_name=site.name,
                extra_data={"discoverer": site.discoverer, "archaeological_context": site.archaeological_context},
            ))

    transfers = load_transfers_by_leaf(leaf_id)
    for t in transfers:
        from_unit = get_collection_unit(t.from_unit_id) if t.from_unit_id else None
        to_unit = get_collection_unit(t.to_unit_id)
        from_name = from_unit.name if from_unit else "发现地点/未知"
        to_name = to_unit.name if to_unit else "未知"
        transfer_names = {
            "discovery": "发现入藏",
            "purchase": "收购",
            "donation": "捐赠",
            "transfer": "调拨",
            "loan": "借展",
            "confiscation": "移交",
            "other": "其他",
        }
        events.append(TimelineEvent(
            event_id=f"transfer_{t.id}",
            event_type="transfer",
            event_date=t.transfer_date,
            title=f"{transfer_names.get(t.transfer_type, t.transfer_type)}：{from_name} → {to_name}",
            description=t.notes or f"从 {from_name} 流转至 {to_name}，入藏号：{t.access_number}",
            location=to_name,
            related_entity_id=t.to_unit_id,
            related_entity_name=to_name,
            extra_data={
                "from_unit_id": t.from_unit_id,
                "from_unit_name": from_name,
                "to_unit_id": t.to_unit_id,
                "access_number": t.access_number,
                "transferred_by": t.transferred_by,
                "document_ref": t.document_ref,
                "condition_report": t.condition_report,
            },
        ))

    repairs = load_repairs_by_leaf(leaf_id)
    for r in repairs:
        repair_names = {
            "conservation": "文物保护",
            "restoration": "修复处理",
            "rebinding": "重装裱",
            "digitization": "数字化扫描",
            "other": "其他处理",
        }
        events.append(TimelineEvent(
            event_id=f"repair_{r.id}",
            event_type="repair",
            event_date=r.repair_date,
            title=f"{repair_names.get(r.repair_type, r.repair_type)}",
            description=f"由 {r.performed_by} 在 {r.location} 进行修复处理",
            location=r.location,
            related_entity_id=r.id,
            related_entity_name=r.performed_by,
            extra_data={
                "repair_type": r.repair_type,
                "before_condition": r.before_condition,
                "after_condition": r.after_condition,
                "materials_used": r.materials_used,
                "techniques_used": r.techniques_used,
                "document_ref": r.document_ref,
            },
        ))

    citations = load_citations_by_leaf(leaf_id)
    for c in citations:
        authors_str = ", ".join(c.authors) if c.authors else ""
        year_str = f"({c.year})" if c.year else ""
        events.append(TimelineEvent(
            event_id=f"citation_{c.id}",
            event_type="citation",
            event_date=str(c.year) if c.year else None,
            title=f"学术引用：{c.title}",
            description=f"{authors_str} {year_str}. {c.title}. {c.journal} {c.volume}({c.issue}):{c.pages}",
            related_entity_id=c.id,
            related_entity_name=authors_str,
            extra_data={
                "citation_type": c.citation_type,
                "authors": c.authors,
                "year": c.year,
                "journal": c.journal,
                "doi": c.doi,
                "url": c.url,
                "cited_content": c.cited_content,
                "keywords": c.keywords,
            },
        ))

    plans = load_all_plans()
    for plan_id, plan in plans.items():
        plan_leaf_ids = [l.leaf_id for l in plan.leaves]
        if leaf_id in plan_leaf_ids:
            plan_order = next((l.order for l in plan.leaves if l.leaf_id == leaf_id), None)
            events.append(TimelineEvent(
                event_id=f"plan_{plan_id}",
                event_type="associated_plan",
                event_date=plan.created_at.strftime("%Y-%m-%d"),
                title=f"纳入复原方案：{plan.name}",
                description=f"在方案中排序位置：第 {plan_order} 位{'（最终方案）' if plan.is_final else ''}",
                related_entity_id=plan_id,
                related_entity_name=plan.name,
                extra_data={
                    "plan_id": plan_id,
                    "plan_name": plan.name,
                    "is_final": plan.is_final,
                    "order": plan_order,
                    "score": plan.score,
                },
            ))

    projects = load_all_collab_projects()
    for pid, proj in projects.items():
        if leaf_id in proj.target_leaf_ids:
            events.append(TimelineEvent(
                event_id=f"consensus_{pid}",
                event_type="consensus",
                event_date=proj.created_at.strftime("%Y-%m-%d"),
                title=f"参与协同校勘项目：{proj.name}",
                description=f"项目状态：{proj.status}，参与研究者 {len(proj.researcher_ids)} 人",
                related_entity_id=pid,
                related_entity_name=proj.name,
                extra_data={
                    "project_id": pid,
                    "project_name": proj.name,
                    "status": proj.status,
                    "researcher_count": len(proj.researcher_ids),
                },
            ))

    events.sort(key=lambda e: _parse_date_sort_key(e.event_date))

    leaf_summary = {
        "id": leaf.id,
        "length": leaf.length,
        "width": leaf.width,
        "confirmed": leaf.confirmed,
        "residual_text": leaf.residual_text,
        "damage": leaf.damage,
        "image_path": leaf.image_path,
        "created_at": leaf.created_at,
        "updated_at": leaf.updated_at,
    }

    return ProvenanceTimeline(
        leaf_id=leaf_id,
        leaf_summary=leaf_summary,
        events=events,
        total_events=len(events),
    )


@router.get("/leaves/{leaf_id}/graph", response_model=ProvenanceGraph)
def get_leaf_provenance_graph(leaf_id: str):
    _validate_leaf_exists(leaf_id)
    leaves = load_all_leaves()
    leaf = leaves[leaf_id]
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []

    leaf_node_id = f"leaf:{leaf_id}"
    nodes.append(GraphNode(
        node_id=leaf_node_id,
        node_type="leaf",
        label=f"叶片 {leaf_id}",
        properties={
            "length": leaf.length,
            "width": leaf.width,
            "confirmed": leaf.confirmed,
            "hole_count": len(leaf.holes),
            "residual_text_preview": leaf.residual_text[:50] if leaf.residual_text else "",
        },
    ))

    site_id = get_leaf_discovery_site_id(leaf_id)
    if site_id:
        site = get_discovery_site(site_id)
        if site:
            site_node_id = f"site:{site_id}"
            nodes.append(GraphNode(
                node_id=site_node_id,
                node_type="site",
                label=site.name,
                properties={
                    "region": site.region,
                    "discovery_date": site.discovery_date,
                    "discoverer": site.discoverer,
                    "latitude": site.latitude,
                    "longitude": site.longitude,
                },
            ))
            edges.append(GraphEdge(
                edge_id=f"edge_discovery_{leaf_id}_{site_id}",
                source_id=leaf_node_id,
                target_id=site_node_id,
                relation_type="discovered_at",
                label=f"发现于 {site.discovery_date or '未知时间'}",
                date=site.discovery_date,
            ))

    transfers = load_transfers_by_leaf(leaf_id)
    unit_node_ids = set()
    for t in transfers:
        for unit_id in ([t.from_unit_id] if t.from_unit_id else []) + [t.to_unit_id]:
            if unit_id and unit_id not in unit_node_ids:
                unit = get_collection_unit(unit_id)
                if unit:
                    unit_node_ids.add(unit_id)
                    nodes.append(GraphNode(
                        node_id=f"unit:{unit_id}",
                        node_type="unit",
                        label=unit.name,
                        properties={
                            "type": unit.type,
                            "country": unit.country,
                            "city": unit.city,
                            "curator": unit.curator,
                        },
                    ))
        if t.from_unit_id:
            edges.append(GraphEdge(
                edge_id=f"edge_transfer_{t.id}",
                source_id=f"unit:{t.from_unit_id}",
                target_id=f"unit:{t.to_unit_id}" if t.to_unit_id in unit_node_ids else "",
                relation_type="transferred_to",
                label=f"{t.transfer_type} ({t.transfer_date or '未知'})",
                date=t.transfer_date,
                properties={
                    "leaf_id": leaf_id,
                    "access_number": t.access_number,
                    "document_ref": t.document_ref,
                },
            ))
        if t.to_unit_id and (not t.from_unit_id):
            edges.append(GraphEdge(
                edge_id=f"edge_housed_{leaf_id}_{t.to_unit_id}",
                source_id=leaf_node_id,
                target_id=f"unit:{t.to_unit_id}",
                relation_type="housed_at",
                label=f"入藏于 {t.transfer_date or '未知时间'}",
                date=t.transfer_date,
            ))

    repairs = load_repairs_by_leaf(leaf_id)
    for r in repairs:
        if r.performed_by:
            person_node_id = f"person:repair_{r.id}"
            if not any(n.node_id == person_node_id for n in nodes):
                nodes.append(GraphNode(
                    node_id=person_node_id,
                    node_type="person",
                    label=r.performed_by,
                    properties={
                        "role": "修复者",
                        "location": r.location,
                    },
                ))
            edges.append(GraphEdge(
                edge_id=f"edge_repair_{r.id}",
                source_id=leaf_node_id,
                target_id=person_node_id,
                relation_type="repaired_by",
                label=f"{r.repair_type} ({r.repair_date or '未知'})",
                date=r.repair_date,
                properties={
                    "document_ref": r.document_ref,
                },
            ))

    citations = load_citations_by_leaf(leaf_id)
    for c in citations:
        pub_node_id = f"publication:{c.id}"
        nodes.append(GraphNode(
            node_id=pub_node_id,
            node_type="publication",
            label=c.title[:30] + ("..." if len(c.title) > 30 else ""),
            properties={
                "authors": c.authors,
                "year": c.year,
                "journal": c.journal,
                "doi": c.doi,
                "citation_type": c.citation_type,
            },
        ))
        edges.append(GraphEdge(
            edge_id=f"edge_citation_{c.id}",
            source_id=leaf_node_id,
            target_id=pub_node_id,
            relation_type="cited_in",
            label=f"引用于 {c.year or '未知年份'}",
            date=str(c.year) if c.year else None,
            properties={
                "language": c.language,
                "keywords": c.keywords,
            },
        ))

    plans = load_all_plans()
    for plan_id, plan in plans.items():
        plan_leaf_ids = [l.leaf_id for l in plan.leaves]
        if leaf_id in plan_leaf_ids:
            plan_node_id = f"plan:{plan_id}"
            nodes.append(GraphNode(
                node_id=plan_node_id,
                node_type="plan",
                label=plan.name,
                properties={
                    "is_final": plan.is_final,
                    "score": plan.score,
                    "total_leaves": len(plan.leaves),
                    "description": plan.description[:50] if plan.description else "",
                },
            ))
            edges.append(GraphEdge(
                edge_id=f"edge_plan_{plan_id}_{leaf_id}",
                source_id=leaf_node_id,
                target_id=plan_node_id,
                relation_type="included_in",
                label=f"包含于复原方案",
                properties={
                    "order": next((l.order for l in plan.leaves if l.leaf_id == leaf_id), None),
                },
            ))

    projects = load_all_collab_projects()
    for pid, proj in projects.items():
        if leaf_id in proj.target_leaf_ids:
            proj_node_id = f"project:{pid}"
            nodes.append(GraphNode(
                node_id=proj_node_id,
                node_type="plan",
                label=f"项目: {proj.name}",
                properties={
                    "status": proj.status,
                    "researcher_count": len(proj.researcher_ids),
                    "target_leaf_count": len(proj.target_leaf_ids),
                },
            ))
            edges.append(GraphEdge(
                edge_id=f"edge_project_{pid}_{leaf_id}",
                source_id=leaf_node_id,
                target_id=proj_node_id,
                relation_type="discussed_in",
                label=f"参与协同校勘",
            ))

    valid_edges = [e for e in edges if e.source_id and e.target_id]

    return ProvenanceGraph(
        leaf_id=leaf_id,
        nodes=nodes,
        edges=valid_edges,
        node_count=len(nodes),
        edge_count=len(valid_edges),
    )


def _calculate_completeness_score(
    has_site: bool,
    has_current_unit: bool,
    transfer_count: int,
    repair_count: int,
    citation_count: int,
    plan_count: int,
    project_count: int,
    has_annotation: bool,
) -> float:
    score = 0.0
    weights = {
        "site": 0.15,
        "current_unit": 0.15,
        "transfers": 0.15,
        "repairs": 0.10,
        "citations": 0.20,
        "plans": 0.10,
        "projects": 0.10,
        "annotation": 0.05,
    }
    if has_site:
        score += weights["site"]
    if has_current_unit:
        score += weights["current_unit"]
    score += weights["transfers"] * min(transfer_count / 3, 1.0)
    score += weights["repairs"] * min(repair_count / 2, 1.0)
    score += weights["citations"] * min(citation_count / 5, 1.0)
    score += weights["plans"] * min(plan_count / 2, 1.0)
    score += weights["projects"] * min(project_count / 1, 1.0)
    if has_annotation:
        score += weights["annotation"]
    return round(score, 3)


def _calculate_reliability_score(
    has_doc_refs: bool,
    has_access_numbers: bool,
    citation_count: int,
    has_archaeological_context: bool,
) -> float:
    score = 0.0
    if has_doc_refs:
        score += 0.3
    if has_access_numbers:
        score += 0.2
    if has_archaeological_context:
        score += 0.2
    score += 0.3 * min(citation_count / 10, 1.0)
    return round(score, 3)


@router.get("/leaves/{leaf_id}/summary", response_model=LeafProvenanceSummary)
def get_leaf_provenance_summary(leaf_id: str):
    _validate_leaf_exists(leaf_id)

    site_id = get_leaf_discovery_site_id(leaf_id)
    discovery_site = get_discovery_site(site_id) if site_id else None

    current_unit = get_leaf_current_unit(leaf_id)

    transfers = load_transfers_by_leaf(leaf_id)
    transfer_count = len(transfers)

    repairs = load_repairs_by_leaf(leaf_id)
    repair_count = len(repairs)

    citations = load_citations_by_leaf(leaf_id)
    citation_count = len(citations)

    plans = load_all_plans()
    associated_plans = []
    for plan_id, plan in plans.items():
        plan_leaf_ids = [l.leaf_id for l in plan.leaves]
        if leaf_id in plan_leaf_ids:
            order = next((l.order for l in plan.leaves if l.leaf_id == leaf_id), None)
            associated_plans.append({
                "plan_id": plan_id,
                "name": plan.name,
                "is_final": plan.is_final,
                "order": order,
                "score": plan.score,
            })

    projects = load_all_collab_projects()
    associated_projects = []
    consensus_info = None
    for pid, proj in projects.items():
        if leaf_id in proj.target_leaf_ids:
            associated_projects.append({
                "project_id": pid,
                "name": proj.name,
                "status": proj.status,
                "researcher_count": len(proj.researcher_ids),
            })
            versions = load_consensus_versions_by_project(pid)
            for v in versions:
                if v.is_final:
                    note = v.consensus_notes.get(leaf_id) if v.consensus_notes else None
                    in_unresolved = leaf_id in (v.unresolved_disputes or [])
                    pos_in_order = next((l.order for l in v.ordered_leaves if l.leaf_id == leaf_id), None)
                    consensus_info = {
                        "project_id": pid,
                        "project_name": proj.name,
                        "version_id": v.id,
                        "version_name": v.name,
                        "version": v.version,
                        "consensus_order": pos_in_order,
                        "consensus_note": note,
                        "is_unresolved": in_unresolved,
                        "approved_by": v.approved_by,
                    }

    annotation = get_annotation(leaf_id)
    associated_annotations = []
    if annotation:
        associated_annotations.append({
            "leaf_id": leaf_id,
            "image_path": annotation.image_path,
            "hole_count": len(annotation.holes),
            "damage_count": len(annotation.damage_regions),
            "text_count": len(annotation.text_regions),
            "scale": annotation.scale,
        })

    has_doc_refs = any(t.document_ref for t in transfers) or any(r.document_ref for r in repairs)
    has_access_numbers = any(t.access_number for t in transfers)
    has_archaeological_context = bool(discovery_site and discovery_site.archaeological_context)

    completeness_score = _calculate_completeness_score(
        has_site=discovery_site is not None,
        has_current_unit=current_unit is not None,
        transfer_count=transfer_count,
        repair_count=repair_count,
        citation_count=citation_count,
        plan_count=len(associated_plans),
        project_count=len(associated_projects),
        has_annotation=len(associated_annotations) > 0,
    )

    reliability_score = _calculate_reliability_score(
        has_doc_refs=has_doc_refs,
        has_access_numbers=has_access_numbers,
        citation_count=citation_count,
        has_archaeological_context=has_archaeological_context,
    )

    return LeafProvenanceSummary(
        leaf_id=leaf_id,
        discovery_site=discovery_site,
        current_unit=current_unit,
        transfer_count=transfer_count,
        repair_count=repair_count,
        citation_count=citation_count,
        associated_plans=associated_plans,
        associated_projects=associated_projects,
        associated_annotations=associated_annotations,
        consensus_summary=consensus_info,
        source_reliability=reliability_score,
        completeness_score=completeness_score,
    )


@router.post("/leaves/{leaf_id}/related", response_model=List[RelatedLeafInfo])
def find_related_leaves(
    leaf_id: str,
    by_site: bool = True,
    by_unit: bool = True,
    by_transfer: bool = True,
    by_citation: bool = True,
    by_plan: bool = True,
):
    _validate_leaf_exists(leaf_id)
    leaves = load_all_leaves()
    related: Dict[str, RelatedLeafInfo] = {}

    if by_site:
        site_id = get_leaf_discovery_site_id(leaf_id)
        if site_id:
            same_site_leaves = get_leaves_by_discovery_site(site_id)
            site = get_discovery_site(site_id)
            for lid in same_site_leaves:
                if lid != leaf_id and lid in leaves:
                    if lid not in related:
                        related[lid] = RelatedLeafInfo(
                            leaf_id=lid,
                            relation_type="same_discovery_site",
                            relation_detail=f"同发现于 {site.name if site else site_id}",
                            strength=0.8,
                        )

    if by_unit:
        current_unit = get_leaf_current_unit(leaf_id)
        if current_unit:
            all_transfers = load_all_provenance_transfers()
            same_unit_leaf_ids = set()
            for t in all_transfers:
                if t.to_unit_id == current_unit.id and t.leaf_id in leaves:
                    same_unit_leaf_ids.add(t.leaf_id)
            for lid in same_unit_leaf_ids:
                if lid != leaf_id:
                    strength = 0.6
                    existing = related.get(lid)
                    if existing:
                        strength = max(existing.strength, strength)
                        detail = existing.relation_detail + f"；同藏于 {current_unit.name}"
                    else:
                        detail = f"同收藏于 {current_unit.name}"
                    related[lid] = RelatedLeafInfo(
                        leaf_id=lid,
                        relation_type=existing.relation_type + ",same_collection_unit" if existing else "same_collection_unit",
                        relation_detail=detail,
                        strength=strength,
                    )

    if by_transfer:
        transfers = load_transfers_by_leaf(leaf_id)
        unit_ids_in_path = set()
        for t in transfers:
            if t.from_unit_id:
                unit_ids_in_path.add(t.from_unit_id)
            if t.to_unit_id:
                unit_ids_in_path.add(t.to_unit_id)
        if unit_ids_in_path:
            all_transfers = load_all_provenance_transfers()
            path_related: Dict[str, set] = {}
            for t in all_transfers:
                if t.leaf_id != leaf_id and t.leaf_id in leaves:
                    for uid in unit_ids_in_path:
                        if t.from_unit_id == uid or t.to_unit_id == uid:
                            if t.leaf_id not in path_related:
                                path_related[t.leaf_id] = set()
                            path_related[t.leaf_id].add(uid)
            for lid, shared_units in path_related.items():
                unit_names = []
                for uid in shared_units:
                    u = get_collection_unit(uid)
                    unit_names.append(u.name if u else uid)
                strength = 0.3 + 0.15 * len(shared_units)
                existing = related.get(lid)
                if existing:
                    strength = max(existing.strength, strength)
                    detail = existing.relation_detail + f"；流转路径重叠（{', '.join(unit_names)}）"
                    rel_type = existing.relation_type + ",shared_transfer_path"
                else:
                    detail = f"流转路径重叠，共同经过：{', '.join(unit_names)}"
                    rel_type = "shared_transfer_path"
                related[lid] = RelatedLeafInfo(
                    leaf_id=lid,
                    relation_type=rel_type,
                    relation_detail=detail,
                    strength=round(strength, 2),
                )

    if by_citation:
        citations = load_citations_by_leaf(leaf_id)
        citation_titles = {c.title for c in citations}
        citation_authors = set()
        for c in citations:
            citation_authors.update(c.authors)
        if citation_titles or citation_authors:
            all_citations = load_all_research_citations()
            cite_related: Dict[str, dict] = {}
            for c in all_citations:
                if c.leaf_id != leaf_id and c.leaf_id in leaves:
                    shared = 0
                    shared_items = []
                    if c.title in citation_titles:
                        shared += 2
                        shared_items.append(f"同被《{c.title}》引用")
                    common_authors = citation_authors & set(c.authors)
                    if common_authors:
                        shared += len(common_authors)
                        shared_items.append(f"共同学者：{', '.join(common_authors)}")
                    if shared > 0:
                        if c.leaf_id not in cite_related:
                            cite_related[c.leaf_id] = {"count": 0, "items": []}
                        cite_related[c.leaf_id]["count"] += shared
                        cite_related[c.leaf_id]["items"].extend(shared_items)
            for lid, info in cite_related.items():
                strength = min(0.3 + 0.08 * info["count"], 0.85)
                existing = related.get(lid)
                if existing:
                    strength = max(existing.strength, strength)
                    detail = existing.relation_detail + "；" + "；".join(info["items"])
                    rel_type = existing.relation_type + ",shared_citation"
                else:
                    detail = "；".join(info["items"])
                    rel_type = "shared_citation"
                related[lid] = RelatedLeafInfo(
                    leaf_id=lid,
                    relation_type=rel_type,
                    relation_detail=detail,
                    strength=round(strength, 2),
                )

    if by_plan:
        plans = load_all_plans()
        plan_ids_with_leaf = set()
        for plan_id, plan in plans.items():
            plan_leaf_ids = [l.leaf_id for l in plan.leaves]
            if leaf_id in plan_leaf_ids:
                plan_ids_with_leaf.add(plan_id)
        if plan_ids_with_leaf:
            plan_related: Dict[str, list] = {}
            for plan_id in plan_ids_with_leaf:
                plan = plans[plan_id]
                for l in plan.leaves:
                    if l.leaf_id != leaf_id and l.leaf_id in leaves:
                        if l.leaf_id not in plan_related:
                            plan_related[l.leaf_id] = []
                        plan_related[l.leaf_id].append(f"方案《{plan.name}》第{l.order}位")
            for lid, plan_info in plan_related.items():
                strength = 0.4 + 0.15 * len(plan_info)
                existing = related.get(lid)
                if existing:
                    strength = max(existing.strength, strength)
                    detail = existing.relation_detail + "；" + "；".join(plan_info)
                    rel_type = existing.relation_type + ",same_reconstruction_plan"
                else:
                    detail = "同处复原方案：" + "；".join(plan_info)
                    rel_type = "same_reconstruction_plan"
                related[lid] = RelatedLeafInfo(
                    leaf_id=lid,
                    relation_type=rel_type,
                    relation_detail=detail,
                    strength=round(strength, 2),
                )

    result = sorted(related.values(), key=lambda r: r.strength, reverse=True)
    return result
