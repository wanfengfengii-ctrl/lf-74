from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class HolePosition(BaseModel):
    x: float = Field(description="穿孔 X 坐标（毫米）")
    y: float = Field(description="穿孔 Y 坐标（毫米）")

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


class ImageHole(BaseModel):
    id: str = Field(description="图片穿孔标注唯一ID")
    x: float = Field(description="穿孔在图片上的 X 坐标（像素）")
    y: float = Field(description="穿孔在图片上的 Y 坐标（像素）")
    real_x: Optional[float] = Field(default=None, description="换算后的实际 X 坐标（毫米）")
    real_y: Optional[float] = Field(default=None, description="换算后的实际 Y 坐标（毫米）")
    note: str = Field(default="", description="备注说明")


class DamageRegion(BaseModel):
    id: str = Field(description="破损区域唯一ID")
    x: float = Field(description="区域左上角 X 坐标（像素）")
    y: float = Field(description="区域左上角 Y 坐标（像素）")
    width: float = Field(description="区域宽度（像素）")
    height: float = Field(description="区域高度（像素）")
    severity: str = Field(default="medium", description="破损程度：mild/medium/severe")
    description: str = Field(default="", description="破损描述")


class TextRegion(BaseModel):
    id: str = Field(description="残文区域唯一ID")
    x: float = Field(description="区域左上角 X 坐标（像素）")
    y: float = Field(description="区域左上角 Y 坐标（像素）")
    width: float = Field(description="区域宽度（像素）")
    height: float = Field(description="区域高度（像素）")
    text: str = Field(default="", description="识别出的文字内容")
    linked_damage_ids: List[str] = Field(default_factory=list, description="关联的破损区域ID列表")


class LeafAnnotation(BaseModel):
    leaf_id: str = Field(description="关联的叶片编号")
    image_path: str = Field(default="", description="高清图片路径")
    image_width: int = Field(default=0, description="图片宽度（像素）")
    image_height: int = Field(default=0, description="图片高度（像素）")
    scale: float = Field(default=1.0, description="像素到毫米的换算比例")
    holes: List[ImageHole] = Field(default_factory=list, description="图片上的穿孔标注")
    damage_regions: List[DamageRegion] = Field(default_factory=list, description="破损区域标注")
    text_regions: List[TextRegion] = Field(default_factory=list, description="残文区域标注")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class LeafAnnotationUpdate(BaseModel):
    image_path: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    scale: Optional[float] = None
    holes: Optional[List[ImageHole]] = None
    damage_regions: Optional[List[DamageRegion]] = None
    text_regions: Optional[List[TextRegion]] = None


class OperationType:
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    UPLOAD = "upload"
    RESTORE = "restore"
    CONFIRM = "confirm"


class OperationLog(BaseModel):
    id: str = Field(description="日志ID")
    operation_type: str = Field(description="操作类型：create/update/delete/upload/restore/confirm")
    target_type: str = Field(description="操作对象类型：leaf/plan/annotation")
    target_id: str = Field(description="操作对象ID")
    operator: str = Field(default="system", description="操作人")
    description: str = Field(default="", description="操作描述")
    before_data: Optional[Dict[str, Any]] = Field(default=None, description="操作前数据快照")
    after_data: Optional[Dict[str, Any]] = Field(default=None, description="操作后数据快照")
    created_at: datetime = Field(default_factory=datetime.now)


class PlanVersion(BaseModel):
    id: str = Field(description="版本ID")
    plan_id: str = Field(description="所属方案ID")
    version: int = Field(description="版本号，从1开始")
    name: str = Field(default="", description="版本名称")
    description: str = Field(default="", description="版本说明")
    leaves: List[Any] = Field(default_factory=list, description="该版本的叶片排序快照")
    score: Optional[float] = Field(default=None, description="该版本的评分")
    is_final: bool = Field(default=False, description="是否为最终版本")
    snapshot_data: Dict[str, Any] = Field(default_factory=dict, description="完整方案快照数据")
    created_at: datetime = Field(default_factory=datetime.now)
    operator: str = Field(default="system", description="创建人")


class PlanVersionCreate(BaseModel):
    name: str = Field(default="")
    description: str = Field(default="")


class LeafOrderDiff(BaseModel):
    leaf_id: str = Field(description="叶片ID")
    order_a: Optional[int] = Field(default=None, description="在方案A中的顺序")
    order_b: Optional[int] = Field(default=None, description="在方案B中的顺序")
    position_changed: bool = Field(default=False, description="位置是否变化")
    flipped_changed: bool = Field(default=False, description="翻面状态是否变化")
    is_disputed: bool = Field(default=False, description="是否为争议叶片")
    dispute_reason: str = Field(default="", description="争议原因")


class PlanComparison(BaseModel):
    plan_a_id: str = Field(description="方案A ID")
    plan_b_id: str = Field(description="方案B ID")
    plan_a_name: str = Field(default="", description="方案A名称")
    plan_b_name: str = Field(default="", description="方案B名称")
    plan_a_score: Optional[float] = Field(default=None, description="方案A评分")
    plan_b_score: Optional[float] = Field(default=None, description="方案B评分")
    score_diff: Optional[float] = Field(default=None, description="评分差异")
    common_leaves: List[str] = Field(default_factory=list, description="两个方案共有的叶片")
    only_in_a: List[str] = Field(default_factory=list, description="仅在方案A中的叶片")
    only_in_b: List[str] = Field(default_factory=list, description="仅在方案B中的叶片")
    order_diffs: List[LeafOrderDiff] = Field(default_factory=list, description="顺序差异列表")
    disputed_leaves: List[str] = Field(default_factory=list, description="争议叶片ID列表")


class Leaf(BaseModel):
    id: str = Field(description="叶片唯一编号，不能重复")
    length: float = Field(gt=0, description="叶片长度（毫米），必须大于 0")
    width: float = Field(gt=0, description="叶片宽度（毫米），必须大于 0")
    holes: List[HolePosition] = Field(default_factory=list, description="穿绳孔坐标列表")
    residual_text: str = Field(default="", description="残存文字内容")
    damage: str = Field(default="", description="破损情况描述")
    confirmed: bool = Field(default=False, description="是否已确认信息无误")
    image_path: str = Field(default="", description="高清图片文件路径")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator("holes")
    @classmethod
    def validate_holes_within_bounds(cls, holes: List[HolePosition], info) -> List[HolePosition]:
        length = info.data.get("length")
        width = info.data.get("width")
        if length is not None and width is not None:
            for i, hole in enumerate(holes):
                if hole.x < 0 or hole.x > width:
                    raise ValueError(f"第 {i + 1} 个穿孔的 X 坐标 {hole.x} 超出叶片宽度范围 [0, {width}]")
                if hole.y < 0 or hole.y > length:
                    raise ValueError(f"第 {i + 1} 个穿孔的 Y 坐标 {hole.y} 超出叶片长度范围 [0, {length}]")
        return holes


class LeafCreate(BaseModel):
    id: str = Field(description="叶片唯一编号")
    length: float = Field(gt=0, description="叶片长度（毫米）")
    width: float = Field(gt=0, description="叶片宽度（毫米）")
    holes: List[HolePosition] = Field(default_factory=list)
    residual_text: str = Field(default="")
    damage: str = Field(default="")
    confirmed: bool = Field(default=False)
    image_path: str = Field(default="")


class LeafUpdate(BaseModel):
    length: Optional[float] = Field(default=None, gt=0)
    width: Optional[float] = Field(default=None, gt=0)
    holes: Optional[List[HolePosition]] = Field(default=None)
    residual_text: Optional[str] = Field(default=None)
    damage: Optional[str] = Field(default=None)
    confirmed: Optional[bool] = Field(default=None)
    image_path: Optional[str] = Field(default=None)


class ReconstructionLeaf(BaseModel):
    leaf_id: str = Field(description="叶片编号")
    order: int = Field(ge=0, description="在复原方案中的顺序，从 0 开始")
    flipped: bool = Field(default=False, description="是否翻面")
    rotated: float = Field(default=0.0, description="旋转角度（度）")


class ReconstructionPlan(BaseModel):
    id: str = Field(description="复原方案编号")
    name: str = Field(description="复原方案名称")
    description: str = Field(default="", description="方案说明")
    leaves: List[ReconstructionLeaf] = Field(default_factory=list, description="方案中的叶片排序列表")
    is_final: bool = Field(default=False, description="是否为最终方案")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    score: Optional[float] = Field(default=None, description="综合评分（自动计算）")

    @model_validator(mode="after")
    def check_no_duplicate_leaves(self) -> "ReconstructionPlan":
        leaf_ids = [l.leaf_id for l in self.leaves]
        if len(leaf_ids) != len(set(leaf_ids)):
            raise ValueError("同一复原方案中不能重复使用同一叶片")
        return self


class ReconstructionPlanCreate(BaseModel):
    id: str = Field(description="复原方案编号")
    name: str = Field(description="复原方案名称")
    description: str = Field(default="")
    leaves: List[ReconstructionLeaf] = Field(default_factory=list)
    is_final: bool = Field(default=False)


class ReconstructionPlanUpdate(BaseModel):
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    leaves: Optional[List[ReconstructionLeaf]] = Field(default=None)
    is_final: Optional[bool] = Field(default=None)


class SortRecommendation(BaseModel):
    leaf_id: str
    score: float
    hole_alignment_score: float
    text_continuity_score: float
    reason: str


class SortResult(BaseModel):
    ordered_leaves: List[SortRecommendation]
    total_score: float


class Researcher(BaseModel):
    id: str = Field(description="研究者唯一ID")
    name: str = Field(description="研究者姓名")
    affiliation: str = Field(default="", description="所属机构")
    email: str = Field(default="", description="联系邮箱")
    expertise: str = Field(default="", description="研究领域/专长")
    created_at: datetime = Field(default_factory=datetime.now)


class ResearcherCreate(BaseModel):
    id: str = Field(description="研究者唯一ID")
    name: str = Field(description="研究者姓名")
    affiliation: str = Field(default="")
    email: str = Field(default="")
    expertise: str = Field(default="")


class ResearcherUpdate(BaseModel):
    name: Optional[str] = None
    affiliation: Optional[str] = None
    email: Optional[str] = None
    expertise: Optional[str] = None


class AnnotationOpinion(BaseModel):
    leaf_id: str = Field(description="叶片ID")
    opinion_type: str = Field(description="意见类型：text(文字)/damage(破损)/hole(穿孔)/other(其他)")
    content: str = Field(description="意见内容")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度 0-1")
    reference: str = Field(default="", description="参考依据")


class DisputeNote(BaseModel):
    id: str = Field(default="", description="争议记录ID")
    leaf_id: str = Field(description="争议叶片ID")
    dispute_type: str = Field(description="争议类型：order(排序)/annotation(标注)/classification(分类)")
    description: str = Field(description="争议描述")
    position: Optional[int] = Field(default=None, description="研究者认为的排序位置")
    flipped: Optional[bool] = Field(default=None, description="研究者认为的翻面状态")
    created_at: datetime = Field(default_factory=datetime.now)


class ResearcherSubmission(BaseModel):
    id: str = Field(description="提交记录ID")
    project_id: str = Field(description="所属协同项目ID")
    researcher_id: str = Field(description="提交者ID")
    researcher_name: str = Field(default="", description="提交者姓名（冗余存储）")
    ordered_leaves: List[ReconstructionLeaf] = Field(default_factory=list, description="研究者提交的叶片排序")
    annotation_opinions: List[AnnotationOpinion] = Field(default_factory=list, description="标注意见列表")
    dispute_notes: List[DisputeNote] = Field(default_factory=list, description="争议说明列表")
    remarks: str = Field(default="", description="整体备注说明")
    submitted_at: datetime = Field(default_factory=datetime.now)
    is_final: bool = Field(default=False, description="是否为最终提交")


class ResearcherSubmissionCreate(BaseModel):
    project_id: str = Field(description="所属协同项目ID")
    researcher_id: str = Field(description="提交者ID")
    ordered_leaves: List[ReconstructionLeaf] = Field(default_factory=list)
    annotation_opinions: List[AnnotationOpinion] = Field(default_factory=list)
    dispute_notes: List[DisputeNote] = Field(default_factory=list)
    remarks: str = Field(default="")
    is_final: bool = Field(default=False)


class CollaborationProject(BaseModel):
    id: str = Field(description="协同项目ID")
    name: str = Field(description="项目名称")
    description: str = Field(default="", description="项目说明")
    target_leaf_ids: List[str] = Field(default_factory=list, description="需要校勘的叶片ID列表")
    researcher_ids: List[str] = Field(default_factory=list, description="参与的研究者ID列表")
    status: str = Field(default="ongoing", description="项目状态：ongoing(进行中)/discussing(讨论中)/finalized(已完成)")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: str = Field(default="system", description="创建者")


class CollaborationProjectCreate(BaseModel):
    id: str = Field(description="协同项目ID")
    name: str = Field(description="项目名称")
    description: str = Field(default="")
    target_leaf_ids: List[str] = Field(default_factory=list)
    researcher_ids: List[str] = Field(default_factory=list)
    created_by: str = Field(default="system")


class CollaborationProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_leaf_ids: Optional[List[str]] = None
    researcher_ids: Optional[List[str]] = None
    status: Optional[str] = None


class LeafPositionVote(BaseModel):
    leaf_id: str = Field(description="叶片ID")
    researcher_id: str = Field(description="研究者ID")
    position: int = Field(description="投票的排序位置")
    flipped: bool = Field(default=False, description="是否翻面")


class LeafConsensus(BaseModel):
    leaf_id: str = Field(description="叶片ID")
    agreed_position: Optional[int] = Field(default=None, description="共识排序位置")
    agreed_flipped: Optional[bool] = Field(default=None, description="共识翻面状态")
    agreement_rate: float = Field(default=0.0, description="一致率 0-1")
    total_votes: int = Field(default=0, description="总投票数")
    position_votes: Dict[int, int] = Field(default_factory=dict, description="各位置投票数 {position: count}")
    flipped_votes: Dict[str, int] = Field(default_factory=dict, description="翻面投票数 {'true': count, 'false': count}")
    is_controversial: bool = Field(default=False, description="是否存在争议")
    disputes: List[DisputeNote] = Field(default_factory=list, description="相关争议记录")


class AnnotationConsensus(BaseModel):
    leaf_id: str = Field(description="叶片ID")
    opinion_type: str = Field(description="意见类型")
    consensus_content: str = Field(default="", description="共识内容")
    agreement_rate: float = Field(default=0.0, description="一致率")
    total_opinions: int = Field(default=0, description="总意见数")
    opinions_by_content: Dict[str, int] = Field(default_factory=dict, description="各内容的意见数")


class CollaborationSummary(BaseModel):
    project_id: str = Field(description="协同项目ID")
    project_name: str = Field(default="", description="项目名称")
    total_researchers: int = Field(default=0, description="参与研究者总数")
    submitted_researchers: int = Field(default=0, description="已提交的研究者数")
    total_leaves: int = Field(default=0, description="目标叶片总数")
    submission_rate: float = Field(default=0.0, description="提交完成率")
    overall_agreement_rate: float = Field(default=0.0, description="整体排序一致率")
    leaf_consensus_list: List[LeafConsensus] = Field(default_factory=list, description="各叶片共识详情")
    annotation_consensus_list: List[AnnotationConsensus] = Field(default_factory=list, description="标注共识详情")
    controversial_leaf_ids: List[str] = Field(default_factory=list, description="存在争议的叶片ID列表")
    top_disputes: List[DisputeNote] = Field(default_factory=list, description="主要争议列表")
    calculated_at: datetime = Field(default_factory=datetime.now)


class DiscussionMessage(BaseModel):
    id: str = Field(description="消息ID")
    project_id: str = Field(description="所属协同项目ID")
    researcher_id: str = Field(description="发言者ID")
    researcher_name: str = Field(default="", description="发言者姓名")
    reply_to_id: Optional[str] = Field(default=None, description="回复的消息ID")
    leaf_id: Optional[str] = Field(default=None, description="关联的叶片ID")
    content: str = Field(description="讨论内容")
    tags: List[str] = Field(default_factory=list, description="标签，如：排序争议/标注疑问/共识确认")
    created_at: datetime = Field(default_factory=datetime.now)
    is_resolved: bool = Field(default=False, description="问题是否已解决")
    resolution_note: str = Field(default="", description="解决说明")


class DiscussionMessageCreate(BaseModel):
    project_id: str = Field(description="所属协同项目ID")
    researcher_id: str = Field(description="发言者ID")
    reply_to_id: Optional[str] = None
    leaf_id: Optional[str] = None
    content: str = Field(description="讨论内容")
    tags: List[str] = Field(default_factory=list)


class DiscussionMessageUpdate(BaseModel):
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    is_resolved: Optional[bool] = None
    resolution_note: Optional[str] = None


class ConsensusVersion(BaseModel):
    id: str = Field(description="共识版本ID")
    project_id: str = Field(description="所属协同项目ID")
    version: int = Field(default=1, description="版本号")
    name: str = Field(default="", description="版本名称")
    description: str = Field(default="", description="版本说明")
    ordered_leaves: List[ReconstructionLeaf] = Field(default_factory=list, description="共识排序结果")
    consensus_notes: Dict[str, str] = Field(default_factory=dict, description="各叶片的共识说明 {leaf_id: note}")
    unresolved_disputes: List[str] = Field(default_factory=list, description="未解决的争议叶片ID列表")
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = Field(default="system", description="创建者")
    approved_by: List[str] = Field(default_factory=list, description="批准的研究者ID列表")
    is_final: bool = Field(default=False, description="是否为最终共识版本")


class ConsensusVersionCreate(BaseModel):
    project_id: str = Field(description="所属协同项目ID")
    name: str = Field(default="")
    description: str = Field(default="")
    ordered_leaves: List[ReconstructionLeaf] = Field(default_factory=list)
    consensus_notes: Dict[str, str] = Field(default_factory=dict)
    unresolved_disputes: List[str] = Field(default_factory=list)
    created_by: str = Field(default="system")
    is_final: bool = Field(default=False)
