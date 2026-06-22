import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .models import (
    Leaf,
    ReconstructionPlan,
    LeafAnnotation,
    OperationLog,
    PlanVersion,
    Researcher,
    CollaborationProject,
    ResearcherSubmission,
    DiscussionMessage,
    ConsensusVersion,
    DiscoverySite,
    CollectionUnit,
    ProvenanceTransfer,
    RepairRecord,
    ResearchCitation,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LEAVES_FILE = os.path.join(DATA_DIR, "leaves.json")
PLANS_FILE = os.path.join(DATA_DIR, "plans.json")
ANNOTATIONS_FILE = os.path.join(DATA_DIR, "annotations.json")
LOGS_FILE = os.path.join(DATA_DIR, "operation_logs.json")
VERSIONS_FILE = os.path.join(DATA_DIR, "plan_versions.json")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
RESEARCHERS_FILE = os.path.join(DATA_DIR, "researchers.json")
COLLAB_PROJECTS_FILE = os.path.join(DATA_DIR, "collab_projects.json")
SUBMISSIONS_FILE = os.path.join(DATA_DIR, "researcher_submissions.json")
DISCUSSIONS_FILE = os.path.join(DATA_DIR, "discussion_messages.json")
CONSENSUS_VERSIONS_FILE = os.path.join(DATA_DIR, "consensus_versions.json")
DISCOVERY_SITES_FILE = os.path.join(DATA_DIR, "discovery_sites.json")
COLLECTION_UNITS_FILE = os.path.join(DATA_DIR, "collection_units.json")
PROVENANCE_TRANSFERS_FILE = os.path.join(DATA_DIR, "provenance_transfers.json")
REPAIR_RECORDS_FILE = os.path.join(DATA_DIR, "repair_records.json")
RESEARCH_CITATIONS_FILE = os.path.join(DATA_DIR, "research_citations.json")
LEAF_SITE_LINKS_FILE = os.path.join(DATA_DIR, "leaf_site_links.json")


def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)


def _read_json(file_path: str) -> Dict:
    _ensure_data_dir()
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        if not content:
            return {}
        return json.loads(content)


def _read_json_list(file_path: str) -> List:
    _ensure_data_dir()
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        if not content:
            return []
        return json.loads(content)


def _write_json(file_path: str, data: Dict):
    _ensure_data_dir()
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def _write_json_list(file_path: str, data: List):
    _ensure_data_dir()
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def load_all_leaves() -> Dict[str, Leaf]:
    raw = _read_json(LEAVES_FILE)
    result = {}
    for leaf_id, leaf_data in raw.items():
        leaf_data["created_at"] = datetime.fromisoformat(leaf_data["created_at"])
        leaf_data["updated_at"] = datetime.fromisoformat(leaf_data["updated_at"])
        result[leaf_id] = Leaf(**leaf_data)
    return result


def save_all_leaves(leaves: Dict[str, Leaf]):
    raw = {}
    for leaf_id, leaf in leaves.items():
        raw[leaf_id] = leaf.model_dump(mode="json")
    _write_json(LEAVES_FILE, raw)


def load_all_plans() -> Dict[str, ReconstructionPlan]:
    raw = _read_json(PLANS_FILE)
    result = {}
    for plan_id, plan_data in raw.items():
        plan_data["created_at"] = datetime.fromisoformat(plan_data["created_at"])
        plan_data["updated_at"] = datetime.fromisoformat(plan_data["updated_at"])
        result[plan_id] = ReconstructionPlan(**plan_data)
    return result


def save_all_plans(plans: Dict[str, ReconstructionPlan]):
    raw = {}
    for plan_id, plan in plans.items():
        raw[plan_id] = plan.model_dump(mode="json")
    _write_json(PLANS_FILE, raw)


def load_all_annotations() -> Dict[str, LeafAnnotation]:
    raw = _read_json(ANNOTATIONS_FILE)
    result = {}
    for leaf_id, data in raw.items():
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        result[leaf_id] = LeafAnnotation(**data)
    return result


def save_annotation(annotation: LeafAnnotation):
    annotations = load_all_annotations()
    annotations[annotation.leaf_id] = annotation
    raw = {}
    for lid, ann in annotations.items():
        raw[lid] = ann.model_dump(mode="json")
    _write_json(ANNOTATIONS_FILE, raw)


def get_annotation(leaf_id: str) -> Optional[LeafAnnotation]:
    annotations = load_all_annotations()
    return annotations.get(leaf_id)


def delete_annotation(leaf_id: str):
    annotations = load_all_annotations()
    if leaf_id in annotations:
        del annotations[leaf_id]
        raw = {}
        for lid, ann in annotations.items():
            raw[lid] = ann.model_dump(mode="json")
        _write_json(ANNOTATIONS_FILE, raw)


def save_image_file(leaf_id: str, filename: str, content: bytes) -> str:
    _ensure_data_dir()
    ext = os.path.splitext(filename)[1] or ".png"
    safe_filename = f"{leaf_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(IMAGES_DIR, safe_filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return os.path.join("images", safe_filename)


def get_image_path(relative_path: str) -> Optional[str]:
    if not relative_path:
        return None
    full_path = os.path.join(DATA_DIR, relative_path)
    if os.path.exists(full_path):
        return full_path
    return None


def add_operation_log(
    operation_type: str,
    target_type: str,
    target_id: str,
    description: str = "",
    operator: str = "system",
    before_data: Optional[Dict] = None,
    after_data: Optional[Dict] = None,
) -> OperationLog:
    logs = load_operation_logs()
    log = OperationLog(
        id=str(uuid.uuid4()),
        operation_type=operation_type,
        target_type=target_type,
        target_id=target_id,
        operator=operator,
        description=description,
        before_data=before_data,
        after_data=after_data,
        created_at=datetime.now(),
    )
    logs.append(log)
    raw_logs = [l.model_dump(mode="json") for l in logs]
    _write_json_list(LOGS_FILE, raw_logs)
    return log


def load_operation_logs(
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    operation_type: Optional[str] = None,
    limit: int = 200,
) -> List[OperationLog]:
    raw = _read_json_list(LOGS_FILE)
    logs = []
    for item in raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        logs.append(OperationLog(**item))

    if target_type:
        logs = [l for l in logs if l.target_type == target_type]
    if target_id:
        logs = [l for l in logs if l.target_id == target_id]
    if operation_type:
        logs = [l for l in logs if l.operation_type == operation_type]

    logs.sort(key=lambda l: l.created_at, reverse=True)
    return logs[:limit]


def get_operation_log(log_id: str) -> Optional[OperationLog]:
    logs = load_operation_logs()
    for log in logs:
        if log.id == log_id:
            return log
    return None


def load_plan_versions(plan_id: str) -> List[PlanVersion]:
    raw = _read_json_list(VERSIONS_FILE)
    versions = []
    for item in raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        v = PlanVersion(**item)
        if v.plan_id == plan_id:
            versions.append(v)
    versions.sort(key=lambda v: v.version, reverse=True)
    return versions


def get_plan_version(version_id: str) -> Optional[PlanVersion]:
    raw = _read_json_list(VERSIONS_FILE)
    for item in raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        v = PlanVersion(**item)
        if v.id == version_id:
            return v
    return None


def save_plan_version(version: PlanVersion) -> PlanVersion:
    versions_raw = _read_json_list(VERSIONS_FILE)
    versions = []
    for item in versions_raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        versions.append(PlanVersion(**item))

    if not version.id:
        version.id = str(uuid.uuid4())
    if not version.created_at:
        version.created_at = datetime.now()

    versions.append(version)
    raw_list = [v.model_dump(mode="json") for v in versions]
    _write_json_list(VERSIONS_FILE, raw_list)
    return version


def get_next_version_number(plan_id: str) -> int:
    existing = load_plan_versions(plan_id)
    if not existing:
        return 1
    return max(v.version for v in existing) + 1


def delete_plan_versions(plan_id: str):
    raw = _read_json_list(VERSIONS_FILE)
    filtered = [item for item in raw if item.get("plan_id") != plan_id]
    _write_json_list(VERSIONS_FILE, filtered)


def load_all_researchers() -> Dict[str, Researcher]:
    raw = _read_json(RESEARCHERS_FILE)
    result = {}
    for r_id, r_data in raw.items():
        r_data["created_at"] = datetime.fromisoformat(r_data["created_at"])
        result[r_id] = Researcher(**r_data)
    return result


def save_all_researchers(researchers: Dict[str, Researcher]):
    raw = {}
    for r_id, r in researchers.items():
        raw[r_id] = r.model_dump(mode="json")
    _write_json(RESEARCHERS_FILE, raw)


def get_researcher(researcher_id: str) -> Optional[Researcher]:
    researchers = load_all_researchers()
    return researchers.get(researcher_id)


def load_all_collab_projects() -> Dict[str, CollaborationProject]:
    raw = _read_json(COLLAB_PROJECTS_FILE)
    result = {}
    for pid, pdata in raw.items():
        pdata["created_at"] = datetime.fromisoformat(pdata["created_at"])
        pdata["updated_at"] = datetime.fromisoformat(pdata["updated_at"])
        result[pid] = CollaborationProject(**pdata)
    return result


def save_all_collab_projects(projects: Dict[str, CollaborationProject]):
    raw = {}
    for pid, p in projects.items():
        raw[pid] = p.model_dump(mode="json")
    _write_json(COLLAB_PROJECTS_FILE, raw)


def get_collab_project(project_id: str) -> Optional[CollaborationProject]:
    projects = load_all_collab_projects()
    return projects.get(project_id)


def load_submissions_by_project(project_id: str) -> List[ResearcherSubmission]:
    raw = _read_json_list(SUBMISSIONS_FILE)
    submissions = []
    for item in raw:
        item["submitted_at"] = datetime.fromisoformat(item["submitted_at"])
        for note in item.get("dispute_notes", []):
            note["created_at"] = datetime.fromisoformat(note["created_at"])
        s = ResearcherSubmission(**item)
        if s.project_id == project_id:
            submissions.append(s)
    submissions.sort(key=lambda s: s.submitted_at, reverse=True)
    return submissions


def load_submission(submission_id: str) -> Optional[ResearcherSubmission]:
    raw = _read_json_list(SUBMISSIONS_FILE)
    for item in raw:
        item["submitted_at"] = datetime.fromisoformat(item["submitted_at"])
        for note in item.get("dispute_notes", []):
            note["created_at"] = datetime.fromisoformat(note["created_at"])
        s = ResearcherSubmission(**item)
        if s.id == submission_id:
            return s
    return None


def save_submission(submission: ResearcherSubmission) -> ResearcherSubmission:
    raw_list = _read_json_list(SUBMISSIONS_FILE)
    existing = []
    for item in raw_list:
        item["submitted_at"] = datetime.fromisoformat(item["submitted_at"])
        for note in item.get("dispute_notes", []):
            note["created_at"] = datetime.fromisoformat(note["created_at"])
        existing.append(ResearcherSubmission(**item))

    if not submission.id:
        submission.id = str(uuid.uuid4())
    if not submission.submitted_at:
        submission.submitted_at = datetime.now()

    existing = [s for s in existing if s.id != submission.id]
    existing.append(submission)
    raw = [s.model_dump(mode="json") for s in existing]
    _write_json_list(SUBMISSIONS_FILE, raw)
    return submission


def load_discussions_by_project(project_id: str) -> List[DiscussionMessage]:
    raw = _read_json_list(DISCUSSIONS_FILE)
    messages = []
    for item in raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        m = DiscussionMessage(**item)
        if m.project_id == project_id:
            messages.append(m)
    messages.sort(key=lambda m: m.created_at)
    return messages


def get_discussion_message(message_id: str) -> Optional[DiscussionMessage]:
    raw = _read_json_list(DISCUSSIONS_FILE)
    for item in raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        m = DiscussionMessage(**item)
        if m.id == message_id:
            return m
    return None


def save_discussion_message(message: DiscussionMessage) -> DiscussionMessage:
    raw_list = _read_json_list(DISCUSSIONS_FILE)
    existing = []
    for item in raw_list:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        existing.append(DiscussionMessage(**item))

    if not message.id:
        message.id = str(uuid.uuid4())
    if not message.created_at:
        message.created_at = datetime.now()

    existing = [m for m in existing if m.id != message.id]
    existing.append(message)
    raw = [m.model_dump(mode="json") for m in existing]
    _write_json_list(DISCUSSIONS_FILE, raw)
    return message


def delete_discussion_message(message_id: str):
    raw = _read_json_list(DISCUSSIONS_FILE)
    filtered = [item for item in raw if item.get("id") != message_id]
    _write_json_list(DISCUSSIONS_FILE, filtered)


def load_consensus_versions_by_project(project_id: str) -> List[ConsensusVersion]:
    raw = _read_json_list(CONSENSUS_VERSIONS_FILE)
    versions = []
    for item in raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        v = ConsensusVersion(**item)
        if v.project_id == project_id:
            versions.append(v)
    versions.sort(key=lambda v: v.version, reverse=True)
    return versions


def get_consensus_version(version_id: str) -> Optional[ConsensusVersion]:
    raw = _read_json_list(CONSENSUS_VERSIONS_FILE)
    for item in raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        v = ConsensusVersion(**item)
        if v.id == version_id:
            return v
    return None


def save_consensus_version(version: ConsensusVersion) -> ConsensusVersion:
    raw_list = _read_json_list(CONSENSUS_VERSIONS_FILE)
    existing = []
    for item in raw_list:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        existing.append(ConsensusVersion(**item))

    if not version.id:
        version.id = str(uuid.uuid4())
    if not version.created_at:
        version.created_at = datetime.now()

    existing = [v for v in existing if v.id != version.id]
    existing.append(version)
    raw = [v.model_dump(mode="json") for v in existing]
    _write_json_list(CONSENSUS_VERSIONS_FILE, raw)
    return version


def get_next_consensus_version_number(project_id: str) -> int:
    existing = load_consensus_versions_by_project(project_id)
    if not existing:
        return 1
    return max(v.version for v in existing) + 1


def load_all_submissions() -> List[ResearcherSubmission]:
    raw = _read_json_list(SUBMISSIONS_FILE)
    result = []
    for item in raw:
        item["submitted_at"] = datetime.fromisoformat(item["submitted_at"])
        for note in item.get("dispute_notes", []):
            if "created_at" in note:
                note["created_at"] = datetime.fromisoformat(note["created_at"])
        result.append(ResearcherSubmission(**item))
    return result


def save_all_submissions(submissions: List[ResearcherSubmission]):
    raw = [s.model_dump(mode="json") for s in submissions]
    _write_json_list(SUBMISSIONS_FILE, raw)


def load_all_discussions() -> List[DiscussionMessage]:
    raw = _read_json_list(DISCUSSIONS_FILE)
    result = []
    for item in raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        result.append(DiscussionMessage(**item))
    return result


def save_all_discussions(messages: List[DiscussionMessage]):
    raw = [m.model_dump(mode="json") for m in messages]
    _write_json_list(DISCUSSIONS_FILE, raw)


def load_all_consensus_versions() -> List[ConsensusVersion]:
    raw = _read_json_list(CONSENSUS_VERSIONS_FILE)
    result = []
    for item in raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        result.append(ConsensusVersion(**item))
    return result


def save_all_consensus_versions(versions: List[ConsensusVersion]):
    raw = [v.model_dump(mode="json") for v in versions]
    _write_json_list(CONSENSUS_VERSIONS_FILE, raw)


def load_all_discovery_sites() -> Dict[str, DiscoverySite]:
    raw = _read_json(DISCOVERY_SITES_FILE)
    result = {}
    for sid, sdata in raw.items():
        sdata["created_at"] = datetime.fromisoformat(sdata["created_at"])
        sdata["updated_at"] = datetime.fromisoformat(sdata["updated_at"])
        result[sid] = DiscoverySite(**sdata)
    return result


def save_all_discovery_sites(sites: Dict[str, DiscoverySite]):
    raw = {}
    for sid, site in sites.items():
        raw[sid] = site.model_dump(mode="json")
    _write_json(DISCOVERY_SITES_FILE, raw)


def get_discovery_site(site_id: str) -> Optional[DiscoverySite]:
    sites = load_all_discovery_sites()
    return sites.get(site_id)


def load_leaf_site_links() -> Dict[str, str]:
    raw = _read_json(LEAF_SITE_LINKS_FILE)
    return dict(raw)


def save_leaf_site_links(links: Dict[str, str]):
    _write_json(LEAF_SITE_LINKS_FILE, links)


def get_leaf_discovery_site_id(leaf_id: str) -> Optional[str]:
    links = load_leaf_site_links()
    return links.get(leaf_id)


def set_leaf_discovery_site(leaf_id: str, site_id: Optional[str]):
    links = load_leaf_site_links()
    if site_id is None:
        if leaf_id in links:
            del links[leaf_id]
    else:
        links[leaf_id] = site_id
    save_leaf_site_links(links)


def get_leaves_by_discovery_site(site_id: str) -> List[str]:
    links = load_leaf_site_links()
    return [lid for lid, sid in links.items() if sid == site_id]


def load_all_collection_units() -> Dict[str, CollectionUnit]:
    raw = _read_json(COLLECTION_UNITS_FILE)
    result = {}
    for uid, udata in raw.items():
        udata["created_at"] = datetime.fromisoformat(udata["created_at"])
        udata["updated_at"] = datetime.fromisoformat(udata["updated_at"])
        result[uid] = CollectionUnit(**udata)
    return result


def save_all_collection_units(units: Dict[str, CollectionUnit]):
    raw = {}
    for uid, unit in units.items():
        raw[uid] = unit.model_dump(mode="json")
    _write_json(COLLECTION_UNITS_FILE, raw)


def get_collection_unit(unit_id: str) -> Optional[CollectionUnit]:
    units = load_all_collection_units()
    return units.get(unit_id)


def load_all_provenance_transfers() -> List[ProvenanceTransfer]:
    raw = _read_json_list(PROVENANCE_TRANSFERS_FILE)
    result = []
    for item in raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        item["updated_at"] = datetime.fromisoformat(item["updated_at"])
        result.append(ProvenanceTransfer(**item))
    return result


def load_transfers_by_leaf(leaf_id: str) -> List[ProvenanceTransfer]:
    all_transfers = load_all_provenance_transfers()
    result = [t for t in all_transfers if t.leaf_id == leaf_id]
    result.sort(key=lambda t: t.transfer_date or "")
    return result


def get_provenance_transfer(transfer_id: str) -> Optional[ProvenanceTransfer]:
    all_transfers = load_all_provenance_transfers()
    for t in all_transfers:
        if t.id == transfer_id:
            return t
    return None


def save_provenance_transfer(transfer: ProvenanceTransfer) -> ProvenanceTransfer:
    raw_list = _read_json_list(PROVENANCE_TRANSFERS_FILE)
    existing = []
    for item in raw_list:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        item["updated_at"] = datetime.fromisoformat(item["updated_at"])
        existing.append(ProvenanceTransfer(**item))

    if not transfer.id:
        transfer.id = str(uuid.uuid4())
    if not transfer.created_at:
        transfer.created_at = datetime.now()

    existing = [t for t in existing if t.id != transfer.id]
    existing.append(transfer)
    raw = [t.model_dump(mode="json") for t in existing]
    _write_json_list(PROVENANCE_TRANSFERS_FILE, raw)
    return transfer


def delete_provenance_transfer(transfer_id: str):
    raw = _read_json_list(PROVENANCE_TRANSFERS_FILE)
    filtered = [item for item in raw if item.get("id") != transfer_id]
    _write_json_list(PROVENANCE_TRANSFERS_FILE, filtered)


def load_all_repair_records() -> List[RepairRecord]:
    raw = _read_json_list(REPAIR_RECORDS_FILE)
    result = []
    for item in raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        item["updated_at"] = datetime.fromisoformat(item["updated_at"])
        result.append(RepairRecord(**item))
    return result


def load_repairs_by_leaf(leaf_id: str) -> List[RepairRecord]:
    all_records = load_all_repair_records()
    result = [r for r in all_records if r.leaf_id == leaf_id]
    result.sort(key=lambda r: r.repair_date or "")
    return result


def get_repair_record(record_id: str) -> Optional[RepairRecord]:
    all_records = load_all_repair_records()
    for r in all_records:
        if r.id == record_id:
            return r
    return None


def save_repair_record(record: RepairRecord) -> RepairRecord:
    raw_list = _read_json_list(REPAIR_RECORDS_FILE)
    existing = []
    for item in raw_list:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        item["updated_at"] = datetime.fromisoformat(item["updated_at"])
        existing.append(RepairRecord(**item))

    if not record.id:
        record.id = str(uuid.uuid4())
    if not record.created_at:
        record.created_at = datetime.now()

    existing = [r for r in existing if r.id != record.id]
    existing.append(record)
    raw = [r.model_dump(mode="json") for r in existing]
    _write_json_list(REPAIR_RECORDS_FILE, raw)
    return record


def delete_repair_record(record_id: str):
    raw = _read_json_list(REPAIR_RECORDS_FILE)
    filtered = [item for item in raw if item.get("id") != record_id]
    _write_json_list(REPAIR_RECORDS_FILE, filtered)


def load_all_research_citations() -> List[ResearchCitation]:
    raw = _read_json_list(RESEARCH_CITATIONS_FILE)
    result = []
    for item in raw:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        item["updated_at"] = datetime.fromisoformat(item["updated_at"])
        result.append(ResearchCitation(**item))
    return result


def load_citations_by_leaf(leaf_id: str) -> List[ResearchCitation]:
    all_citations = load_all_research_citations()
    result = [c for c in all_citations if c.leaf_id == leaf_id]
    result.sort(key=lambda c: c.year or 0, reverse=True)
    return result


def get_research_citation(citation_id: str) -> Optional[ResearchCitation]:
    all_citations = load_all_research_citations()
    for c in all_citations:
        if c.id == citation_id:
            return c
    return None


def save_research_citation(citation: ResearchCitation) -> ResearchCitation:
    raw_list = _read_json_list(RESEARCH_CITATIONS_FILE)
    existing = []
    for item in raw_list:
        item["created_at"] = datetime.fromisoformat(item["created_at"])
        item["updated_at"] = datetime.fromisoformat(item["updated_at"])
        existing.append(ResearchCitation(**item))

    if not citation.id:
        citation.id = str(uuid.uuid4())
    if not citation.created_at:
        citation.created_at = datetime.now()

    existing = [c for c in existing if c.id != citation.id]
    existing.append(citation)
    raw = [c.model_dump(mode="json") for c in existing]
    _write_json_list(RESEARCH_CITATIONS_FILE, raw)
    return citation


def delete_research_citation(citation_id: str):
    raw = _read_json_list(RESEARCH_CITATIONS_FILE)
    filtered = [item for item in raw if item.get("id") != citation_id]
    _write_json_list(RESEARCH_CITATIONS_FILE, filtered)


def get_leaf_current_unit(leaf_id: str) -> Optional[CollectionUnit]:
    transfers = load_transfers_by_leaf(leaf_id)
    if not transfers:
        return None
    last_transfer = transfers[-1]
    return get_collection_unit(last_transfer.to_unit_id)
