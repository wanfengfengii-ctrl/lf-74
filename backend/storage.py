import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from .models import Leaf, ReconstructionPlan

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LEAVES_FILE = os.path.join(DATA_DIR, "leaves.json")
PLANS_FILE = os.path.join(DATA_DIR, "plans.json")


def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def _read_json(file_path: str) -> Dict:
    _ensure_data_dir()
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        if not content:
            return {}
        return json.loads(content)


def _write_json(file_path: str, data: Dict):
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
