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
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LEAVES_FILE = os.path.join(DATA_DIR, "leaves.json")
PLANS_FILE = os.path.join(DATA_DIR, "plans.json")
ANNOTATIONS_FILE = os.path.join(DATA_DIR, "annotations.json")
LOGS_FILE = os.path.join(DATA_DIR, "operation_logs.json")
VERSIONS_FILE = os.path.join(DATA_DIR, "plan_versions.json")
IMAGES_DIR = os.path.join(DATA_DIR, "images")


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
