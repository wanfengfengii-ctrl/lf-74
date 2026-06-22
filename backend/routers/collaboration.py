import uuid
from datetime import datetime
from typing import Dict, List, Optional
from collections import Counter, defaultdict

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from ..models import (
    Researcher,
    ResearcherCreate,
    ResearcherUpdate,
    CollaborationProject,
    CollaborationProjectCreate,
    CollaborationProjectUpdate,
    ResearcherSubmission,
    ResearcherSubmissionCreate,
    DiscussionMessage,
    DiscussionMessageCreate,
    DiscussionMessageUpdate,
    ConsensusVersion,
    ConsensusVersionCreate,
    CollaborationSummary,
    LeafConsensus,
    AnnotationConsensus,
    OperationType,
)
from ..storage import (
    load_all_leaves,
    load_all_researchers,
    save_all_researchers,
    get_researcher,
    load_all_collab_projects,
    save_all_collab_projects,
    get_collab_project,
    load_submissions_by_project,
    load_submission,
    save_submission,
    load_discussions_by_project,
    get_discussion_message,
    save_discussion_message,
    delete_discussion_message,
    load_consensus_versions_by_project,
    get_consensus_version,
    save_consensus_version,
    get_next_consensus_version_number,
    add_operation_log,
)

router = APIRouter(prefix="/collaboration", tags=["多研究者协同校勘"])


@router.get("/researchers", response_model=List[Researcher])
def list_researchers():
    researchers = load_all_researchers()
    return sorted(researchers.values(), key=lambda r: r.created_at, reverse=True)


@router.get("/researchers/{researcher_id}", response_model=Researcher)
def get_researcher_detail(researcher_id: str):
    researcher = get_researcher(researcher_id)
    if not researcher:
        raise HTTPException(status_code=404, detail=f"研究者 '{researcher_id}' 不存在")
    return researcher


@router.post("/researchers", response_model=Researcher)
def create_researcher(data: ResearcherCreate):
    researchers = load_all_researchers()
    if data.id in researchers:
        raise HTTPException(status_code=400, detail=f"研究者编号 '{data.id}' 已存在")
    now = datetime.now()
    try:
        researcher = Researcher(**data.model_dump(), created_at=now)
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    researchers[researcher.id] = researcher
    save_all_researchers(researchers)
    add_operation_log(
        operation_type=OperationType.CREATE,
        target_type="researcher",
        target_id=researcher.id,
        description=f"创建研究者 '{researcher.name}' ({researcher.id})",
        after_data=researcher.model_dump(mode="json"),
    )
    return researcher


@router.put("/researchers/{researcher_id}", response_model=Researcher)
def update_researcher(researcher_id: str, data: ResearcherUpdate):
    researchers = load_all_researchers()
    if researcher_id not in researchers:
        raise HTTPException(status_code=404, detail=f"研究者 '{researcher_id}' 不存在")
    existing = researchers[researcher_id]
    before_data = existing.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing, field, value)
    try:
        existing = Researcher.model_validate(existing.model_dump())
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    researchers[researcher_id] = existing
    save_all_researchers(researchers)
    add_operation_log(
        operation_type=OperationType.UPDATE,
        target_type="researcher",
        target_id=researcher_id,
        description=f"更新研究者 '{existing.name}' 信息",
        before_data=before_data,
        after_data=existing.model_dump(mode="json"),
    )
    return existing


@router.delete("/researchers/{researcher_id}")
def delete_researcher(researcher_id: str):
    researchers = load_all_researchers()
    if researcher_id not in researchers:
        raise HTTPException(status_code=404, detail=f"研究者 '{researcher_id}' 不存在")
    before_data = researchers[researcher_id].model_dump(mode="json")
    name = researchers[researcher_id].name
    del researchers[researcher_id]
    save_all_researchers(researchers)
    add_operation_log(
        operation_type=OperationType.DELETE,
        target_type="researcher",
        target_id=researcher_id,
        description=f"删除研究者 '{name}' ({researcher_id})",
        before_data=before_data,
    )
    return {"message": f"研究者 '{researcher_id}' 已删除"}


@router.get("/projects", response_model=List[CollaborationProject])
def list_collab_projects():
    projects = load_all_collab_projects()
    return sorted(projects.values(), key=lambda p: p.created_at, reverse=True)


@router.get("/projects/{project_id}", response_model=CollaborationProject)
def get_collab_project_detail(project_id: str):
    project = get_collab_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"协同项目 '{project_id}' 不存在")
    return project


@router.post("/projects", response_model=CollaborationProject)
def create_collab_project(data: CollaborationProjectCreate):
    projects = load_all_collab_projects()
    if data.id in projects:
        raise HTTPException(status_code=400, detail=f"协同项目编号 '{data.id}' 已存在")
    researchers = load_all_researchers()
    for rid in data.researcher_ids:
        if rid not in researchers:
            raise HTTPException(status_code=400, detail=f"研究者 '{rid}' 不存在")
    leaves = load_all_leaves()
    for lid in data.target_leaf_ids:
        if lid not in leaves:
            raise HTTPException(status_code=400, detail=f"叶片 '{lid}' 不存在")
    now = datetime.now()
    try:
        project = CollaborationProject(
            **data.model_dump(),
            created_at=now,
            updated_at=now,
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    projects[project.id] = project
    save_all_collab_projects(projects)
    add_operation_log(
        operation_type=OperationType.CREATE,
        target_type="collab_project",
        target_id=project.id,
        description=f"创建协同项目 '{project.name}' ({project.id})",
        after_data=project.model_dump(mode="json"),
    )
    return project


@router.put("/projects/{project_id}", response_model=CollaborationProject)
def update_collab_project(project_id: str, data: CollaborationProjectUpdate):
    projects = load_all_collab_projects()
    if project_id not in projects:
        raise HTTPException(status_code=404, detail=f"协同项目 '{project_id}' 不存在")
    existing = projects[project_id]
    before_data = existing.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)

    if "researcher_ids" in update_data:
        researchers = load_all_researchers()
        for rid in update_data["researcher_ids"]:
            if rid not in researchers:
                raise HTTPException(status_code=400, detail=f"研究者 '{rid}' 不存在")
    if "target_leaf_ids" in update_data:
        leaves = load_all_leaves()
        for lid in update_data["target_leaf_ids"]:
            if lid not in leaves:
                raise HTTPException(status_code=400, detail=f"叶片 '{lid}' 不存在")

    for field, value in update_data.items():
        setattr(existing, field, value)
    existing.updated_at = datetime.now()
    try:
        existing = CollaborationProject.model_validate(existing.model_dump())
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    projects[project_id] = existing
    save_all_collab_projects(projects)
    add_operation_log(
        operation_type=OperationType.UPDATE,
        target_type="collab_project",
        target_id=project_id,
        description=f"更新协同项目 '{existing.name}'",
        before_data=before_data,
        after_data=existing.model_dump(mode="json"),
    )
    return existing


@router.delete("/projects/{project_id}")
def delete_collab_project(project_id: str):
    projects = load_all_collab_projects()
    if project_id not in projects:
        raise HTTPException(status_code=404, detail=f"协同项目 '{project_id}' 不存在")
    before_data = projects[project_id].model_dump(mode="json")
    name = projects[project_id].name
    del projects[project_id]
    save_all_collab_projects(projects)
    add_operation_log(
        operation_type=OperationType.DELETE,
        target_type="collab_project",
        target_id=project_id,
        description=f"删除协同项目 '{name}' ({project_id})",
        before_data=before_data,
    )
    return {"message": f"协同项目 '{project_id}' 已删除"}


@router.get("/projects/{project_id}/submissions", response_model=List[ResearcherSubmission])
def list_project_submissions(project_id: str):
    if not get_collab_project(project_id):
        raise HTTPException(status_code=404, detail=f"协同项目 '{project_id}' 不存在")
    return load_submissions_by_project(project_id)


@router.post("/submissions", response_model=ResearcherSubmission)
def create_submission(data: ResearcherSubmissionCreate):
    project = get_collab_project(data.project_id)
    if not project:
        raise HTTPException(status_code=400, detail=f"协同项目 '{data.project_id}' 不存在")
    researcher = get_researcher(data.researcher_id)
    if not researcher:
        raise HTTPException(status_code=400, detail=f"研究者 '{data.researcher_id}' 不存在")
    if data.researcher_id not in project.researcher_ids:
        raise HTTPException(status_code=400, detail=f"研究者 '{data.researcher_id}' 未参与此项目")
    leaves = load_all_leaves()
    leaf_id_set = set(project.target_leaf_ids)
    for rl in data.ordered_leaves:
        if rl.leaf_id not in leaves:
            raise HTTPException(status_code=400, detail=f"叶片 '{rl.leaf_id}' 不存在")
        if rl.leaf_id not in leaf_id_set:
            raise HTTPException(status_code=400, detail=f"叶片 '{rl.leaf_id}' 不在项目目标范围内")
    for note in data.dispute_notes:
        if note.leaf_id not in leaf_id_set:
            raise HTTPException(status_code=400, detail=f"争议叶片 '{note.leaf_id}' 不在项目目标范围内")
    now = datetime.now()
    for note in data.dispute_notes:
        if not note.id:
            note.id = str(uuid.uuid4())
        if not note.created_at:
            note.created_at = now
    try:
        submission = ResearcherSubmission(
            **data.model_dump(),
            id=str(uuid.uuid4()),
            researcher_name=researcher.name,
            submitted_at=now,
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    submission = save_submission(submission)
    add_operation_log(
        operation_type=OperationType.CREATE,
        target_type="submission",
        target_id=submission.id,
        description=f"研究者 '{researcher.name}' 提交校勘结果到项目 '{project.name}'",
        after_data=submission.model_dump(mode="json"),
    )
    return submission


@router.get("/submissions/{submission_id}", response_model=ResearcherSubmission)
def get_submission_detail(submission_id: str):
    submission = load_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail=f"提交记录 '{submission_id}' 不存在")
    return submission


def _calc_collab_summary(project_id: str) -> CollaborationSummary:
    project = get_collab_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"协同项目 '{project_id}' 不存在")

    submissions = load_submissions_by_project(project_id)
    target_leaf_ids = project.target_leaf_ids
    total_researchers = len(project.researcher_ids)
    submitted_researcher_ids = set()
    position_votes: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
    flipped_votes: Dict[str, Counter] = defaultdict(lambda: Counter())
    annotation_opinions: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    all_disputes_by_leaf: Dict[str, List] = defaultdict(list)

    for sub in submissions:
        submitted_researcher_ids.add(sub.researcher_id)
        for rl in sub.ordered_leaves:
            position_votes[rl.leaf_id][rl.order] += 1
            flipped_votes[rl.leaf_id][str(rl.flipped).lower()] += 1
        for op in sub.annotation_opinions:
            annotation_opinions[op.leaf_id][op.opinion_type].append(op.content)
        for note in sub.dispute_notes:
            all_disputes_by_leaf[note.leaf_id].append(note)

    total_leaves = len(target_leaf_ids)
    submitted_count = len(submitted_researcher_ids)
    submission_rate = submitted_count / max(total_researchers, 1)

    leaf_consensus_list: List[LeafConsensus] = []
    controversial_leaves: List[str] = []
    all_top_disputes: List = []
    total_agreement_sum = 0.0
    valid_leaf_count = 0

    for leaf_id in target_leaf_ids:
        pos_dict = dict(position_votes[leaf_id])
        flip_counter = flipped_votes[leaf_id]
        total_votes = sum(pos_dict.values())
        is_controversial = False

        agreed_position = None
        if pos_dict:
            max_pos_count = max(pos_dict.values())
            for pos, cnt in pos_dict.items():
                if cnt == max_pos_count:
                    agreed_position = pos
                    break
        max_flip_count = 0
        agreed_flipped = None
        if flip_counter:
            most_common = flip_counter.most_common(1)
            if most_common:
                agreed_flipped_str, max_flip_count = most_common[0]
                agreed_flipped = agreed_flipped_str == "true"

        pos_agreement = 0.0
        if total_votes > 0 and agreed_position is not None:
            pos_agreement = pos_dict[agreed_position] / total_votes

        flip_agreement = 0.0
        flip_total = sum(flip_counter.values())
        if flip_total > 0 and agreed_flipped is not None:
            flip_agreement = max_flip_count / flip_total

        combined_agreement = (pos_agreement + flip_agreement) / 2 if (pos_agreement or flip_agreement) else 0.0

        if total_votes > 0:
            total_agreement_sum += combined_agreement
            valid_leaf_count += 1

        disputes = all_disputes_by_leaf.get(leaf_id, [])
        if disputes or (total_votes > 1 and combined_agreement < 0.7):
            is_controversial = True
            controversial_leaves.append(leaf_id)
            all_top_disputes.extend(disputes)

        leaf_consensus_list.append(
            LeafConsensus(
                leaf_id=leaf_id,
                agreed_position=agreed_position,
                agreed_flipped=agreed_flipped,
                agreement_rate=round(combined_agreement, 4),
                total_votes=total_votes,
                position_votes={str(k): v for k, v in pos_dict.items()},
                flipped_votes=dict(flip_counter),
                is_controversial=is_controversial,
                disputes=disputes,
            )
        )

    annotation_consensus_list: List[AnnotationConsensus] = []
    for leaf_id, type_map in annotation_opinions.items():
        for opinion_type, contents in type_map.items():
            content_counter = Counter(contents)
            total = len(contents)
            if total == 0:
                continue
            consensus_content, max_count = content_counter.most_common(1)[0]
            agreement_rate = max_count / total
            annotation_consensus_list.append(
                AnnotationConsensus(
                    leaf_id=leaf_id,
                    opinion_type=opinion_type,
                    consensus_content=consensus_content,
                    agreement_rate=round(agreement_rate, 4),
                    total_opinions=total,
                    opinions_by_content=dict(content_counter),
                )
            )

    overall_agreement_rate = total_agreement_sum / max(valid_leaf_count, 1)
    all_top_disputes.sort(key=lambda d: d.created_at, reverse=True)

    return CollaborationSummary(
        project_id=project.id,
        project_name=project.name,
        total_researchers=total_researchers,
        submitted_researchers=submitted_count,
        total_leaves=total_leaves,
        submission_rate=round(submission_rate, 4),
        overall_agreement_rate=round(overall_agreement_rate, 4),
        leaf_consensus_list=sorted(leaf_consensus_list, key=lambda x: x.agreement_rate),
        annotation_consensus_list=annotation_consensus_list,
        controversial_leaf_ids=controversial_leaves,
        top_disputes=all_top_disputes[:50],
        calculated_at=datetime.now(),
    )


@router.get("/projects/{project_id}/summary", response_model=CollaborationSummary)
def get_collab_summary(project_id: str):
    return _calc_collab_summary(project_id)


@router.get("/projects/{project_id}/discussions", response_model=List[DiscussionMessage])
def list_project_discussions(project_id: str):
    if not get_collab_project(project_id):
        raise HTTPException(status_code=404, detail=f"协同项目 '{project_id}' 不存在")
    return load_discussions_by_project(project_id)


@router.post("/discussions", response_model=DiscussionMessage)
def create_discussion_message(data: DiscussionMessageCreate):
    project = get_collab_project(data.project_id)
    if not project:
        raise HTTPException(status_code=400, detail=f"协同项目 '{data.project_id}' 不存在")
    researcher = get_researcher(data.researcher_id)
    if not researcher:
        raise HTTPException(status_code=400, detail=f"研究者 '{data.researcher_id}' 不存在")
    if data.researcher_id not in project.researcher_ids:
        raise HTTPException(status_code=400, detail=f"研究者 '{data.researcher_id}' 未参与此项目")
    if data.reply_to_id:
        reply_msg = get_discussion_message(data.reply_to_id)
        if not reply_msg:
            raise HTTPException(status_code=400, detail=f"回复的消息 '{data.reply_to_id}' 不存在")
    try:
        message = DiscussionMessage(
            **data.model_dump(),
            id=str(uuid.uuid4()),
            researcher_name=researcher.name,
            created_at=datetime.now(),
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    message = save_discussion_message(message)
    add_operation_log(
        operation_type=OperationType.CREATE,
        target_type="discussion",
        target_id=message.id,
        description=f"研究者 '{researcher.name}' 在项目 '{project.name}' 中发表讨论",
        after_data=message.model_dump(mode="json"),
    )
    return message


@router.put("/discussions/{message_id}", response_model=DiscussionMessage)
def update_discussion_message(message_id: str, data: DiscussionMessageUpdate):
    message = get_discussion_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail=f"讨论消息 '{message_id}' 不存在")
    before_data = message.model_dump(mode="json")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(message, field, value)
    try:
        message = DiscussionMessage.model_validate(message.model_dump())
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    message = save_discussion_message(message)
    add_operation_log(
        operation_type=OperationType.UPDATE,
        target_type="discussion",
        target_id=message_id,
        description=f"更新讨论消息",
        before_data=before_data,
        after_data=message.model_dump(mode="json"),
    )
    return message


@router.delete("/discussions/{message_id}")
def delete_discussion(message_id: str):
    message = get_discussion_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail=f"讨论消息 '{message_id}' 不存在")
    before_data = message.model_dump(mode="json")
    delete_discussion_message(message_id)
    add_operation_log(
        operation_type=OperationType.DELETE,
        target_type="discussion",
        target_id=message_id,
        description=f"删除讨论消息",
        before_data=before_data,
    )
    return {"message": f"讨论消息 '{message_id}' 已删除"}


@router.get("/projects/{project_id}/consensus-versions", response_model=List[ConsensusVersion])
def list_consensus_versions(project_id: str):
    if not get_collab_project(project_id):
        raise HTTPException(status_code=404, detail=f"协同项目 '{project_id}' 不存在")
    return load_consensus_versions_by_project(project_id)


@router.post("/consensus-versions", response_model=ConsensusVersion)
def create_consensus_version(data: ConsensusVersionCreate):
    project = get_collab_project(data.project_id)
    if not project:
        raise HTTPException(status_code=400, detail=f"协同项目 '{data.project_id}' 不存在")
    leaves = load_all_leaves()
    leaf_id_set = set(project.target_leaf_ids)
    for rl in data.ordered_leaves:
        if rl.leaf_id not in leaves:
            raise HTTPException(status_code=400, detail=f"叶片 '{rl.leaf_id}' 不存在")
        if rl.leaf_id not in leaf_id_set:
            raise HTTPException(status_code=400, detail=f"叶片 '{rl.leaf_id}' 不在项目目标范围内")
    version_num = get_next_consensus_version_number(data.project_id)
    try:
        version = ConsensusVersion(
            **data.model_dump(),
            id=str(uuid.uuid4()),
            version=version_num,
            created_at=datetime.now(),
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    version = save_consensus_version(version)
    add_operation_log(
        operation_type=OperationType.CREATE,
        target_type="consensus_version",
        target_id=version.id,
        description=f"创建项目 '{project.name}' 的共识版本 v{version.version}",
        after_data=version.model_dump(mode="json"),
    )
    return version


@router.get("/consensus-versions/{version_id}", response_model=ConsensusVersion)
def get_consensus_version_detail(version_id: str):
    version = get_consensus_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"共识版本 '{version_id}' 不存在")
    return version


@router.post("/consensus-versions/{version_id}/approve", response_model=ConsensusVersion)
def approve_consensus_version(version_id: str, researcher_id: str):
    version = get_consensus_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"共识版本 '{version_id}' 不存在")
    researcher = get_researcher(researcher_id)
    if not researcher:
        raise HTTPException(status_code=400, detail=f"研究者 '{researcher_id}' 不存在")
    project = get_collab_project(version.project_id)
    if not project or researcher_id not in project.researcher_ids:
        raise HTTPException(status_code=400, detail=f"研究者 '{researcher_id}' 未参与此项目")
    before_data = version.model_dump(mode="json")
    if researcher_id not in version.approved_by:
        version.approved_by.append(researcher_id)

    approved_set = set(version.approved_by)
    required_set = set(project.researcher_ids)
    if not version.is_final and len(required_set) > 0 and required_set.issubset(approved_set):
        version.is_final = True
        all_projects = load_all_collab_projects()
        if version.project_id in all_projects:
            updated_project = all_projects[version.project_id]
            project_before = updated_project.model_dump(mode="json")
            updated_project.status = "finalized"
            updated_project.updated_at = datetime.now()
            all_projects[version.project_id] = updated_project
            save_all_collab_projects(all_projects)
            add_operation_log(
                operation_type=OperationType.UPDATE,
                target_type="collaboration_project",
                target_id=project.id,
                description=f"共识版本 v{version.version} 获得全员批准，项目状态自动变更为 finalized",
                before_data=project_before,
                after_data=updated_project.model_dump(mode="json"),
            )

    version = save_consensus_version(version)
    add_operation_log(
        operation_type=OperationType.CONFIRM,
        target_type="consensus_version",
        target_id=version_id,
        description=f"研究者 '{researcher.name}' 批准共识版本 v{version.version}{'（全员已批准，自动设为最终版）' if version.is_final else ''}",
        before_data=before_data,
        after_data=version.model_dump(mode="json"),
    )
    return version


@router.post("/projects/{project_id}/consensus-versions/generate", response_model=ConsensusVersion)
def generate_consensus_from_summary(project_id: str, created_by: str = "system"):
    project = get_collab_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"协同项目 '{project_id}' 不存在")
    summary = _calc_collab_summary(project_id)
    ordered_leaves = []
    consensus_notes: Dict[str, str] = {}
    unresolved_disputes: List[str] = []

    position_map: Dict[int, List[LeafConsensus]] = defaultdict(list)
    no_position_leaves = []
    for lc in summary.leaf_consensus_list:
        if lc.agreed_position is not None:
            position_map[lc.agreed_position].append(lc)
        else:
            no_position_leaves.append(lc)

    sorted_positions = sorted(position_map.keys())
    next_order = 0
    for pos in sorted_positions:
        for lc in position_map[pos]:
            ordered_leaves.append({
                "leaf_id": lc.leaf_id,
                "order": next_order,
                "flipped": lc.agreed_flipped or False,
                "rotated": 0.0,
            })
            note_parts = []
            note_parts.append(f"一致率: {lc.agreement_rate:.0%}")
            if lc.is_controversial:
                note_parts.append("存在争议")
                unresolved_disputes.append(lc.leaf_id)
            if note_parts:
                consensus_notes[lc.leaf_id] = "；".join(note_parts)
            next_order += 1

    for lc in no_position_leaves:
        ordered_leaves.append({
            "leaf_id": lc.leaf_id,
            "order": next_order,
            "flipped": lc.agreed_flipped or False,
            "rotated": 0.0,
        })
        consensus_notes[lc.leaf_id] = f"未达成完全共识（投票 {lc.total_votes}）"
        unresolved_disputes.append(lc.leaf_id)
        next_order += 1

    version_num = get_next_consensus_version_number(project_id)
    try:
        version = ConsensusVersion(
            id=str(uuid.uuid4()),
            project_id=project_id,
            version=version_num,
            name=f"自动共识 v{version_num}",
            description=f"基于 {summary.submitted_researchers} 位研究者提交自动生成的共识版本，整体一致率 {summary.overall_agreement_rate:.0%}",
            ordered_leaves=ordered_leaves,
            consensus_notes=consensus_notes,
            unresolved_disputes=unresolved_disputes,
            created_at=datetime.now(),
            created_by=created_by,
            approved_by=[],
            is_final=False,
        )
    except ValidationError as e:
        detail = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=detail)
    version = save_consensus_version(version)
    add_operation_log(
        operation_type=OperationType.CREATE,
        target_type="consensus_version",
        target_id=version.id,
        description=f"自动生成项目 '{project.name}' 的共识版本 v{version.version}",
        after_data=version.model_dump(mode="json"),
    )
    return version
