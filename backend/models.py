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


class DiscoverySite(BaseModel):
    id: str = Field(description="发现地点唯一ID")
    name: str = Field(description="地点名称，如：敦煌莫高窟第17窟")
    region: str = Field(default="", description="所属地区/省份")
    latitude: Optional[float] = Field(default=None, description="纬度")
    longitude: Optional[float] = Field(default=None, description="经度")
    discovery_date: Optional[str] = Field(default=None, description="发现日期（YYYY-MM-DD或年份）")
    discoverer: str = Field(default="", description="发现者/考察队")
    description: str = Field(default="", description="详细描述，包括地层、环境等")
    archaeological_context: str = Field(default="", description="考古背景信息")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DiscoverySiteCreate(BaseModel):
    id: str = Field(description="发现地点唯一ID")
    name: str = Field(description="地点名称")
    region: str = Field(default="")
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    discovery_date: Optional[str] = Field(default=None)
    discoverer: str = Field(default="")
    description: str = Field(default="")
    archaeological_context: str = Field(default="")


class DiscoverySiteUpdate(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    discovery_date: Optional[str] = None
    discoverer: Optional[str] = None
    description: Optional[str] = None
    archaeological_context: Optional[str] = None


class CollectionUnit(BaseModel):
    id: str = Field(description="收藏单位唯一ID")
    name: str = Field(description="单位名称，如：大英图书馆")
    type: str = Field(default="library", description="单位类型：library/museum/archive/university/private/other")
    country: str = Field(default="", description="所属国家")
    city: str = Field(default="", description="所在城市")
    address: str = Field(default="", description="详细地址")
    contact: str = Field(default="", description="联系方式")
    curator: str = Field(default="", description="负责人/馆长")
    description: str = Field(default="", description="单位介绍与收藏特色")
    established_year: Optional[int] = Field(default=None, description="成立年份")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CollectionUnitCreate(BaseModel):
    id: str = Field(description="收藏单位唯一ID")
    name: str = Field(description="单位名称")
    type: str = Field(default="library")
    country: str = Field(default="")
    city: str = Field(default="")
    address: str = Field(default="")
    contact: str = Field(default="")
    curator: str = Field(default="")
    description: str = Field(default="")
    established_year: Optional[int] = Field(default=None)


class CollectionUnitUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    curator: Optional[str] = None
    description: Optional[str] = None
    established_year: Optional[int] = None


class ProvenanceTransfer(BaseModel):
    id: Optional[str] = Field(default=None, description="流转记录唯一ID")
    leaf_id: str = Field(description="关联的叶片ID")
    transfer_date: Optional[str] = Field(default=None, description="流转日期（YYYY-MM-DD或年份区间）")
    from_unit_id: Optional[str] = Field(default=None, description="转出收藏单位ID，None表示首次入藏/发现")
    to_unit_id: str = Field(description="转入收藏单位ID")
    transfer_type: str = Field(default="transfer", description="流转类型：discovery/purchase/donation/transfer/loan/confiscation/other")
    transferred_by: str = Field(default="", description="经手人/经办人")
    document_ref: str = Field(default="", description="相关凭证/档案编号")
    access_number: str = Field(default="", description="入藏编号/登记号")
    condition_report: str = Field(default="", description="流转时的品相报告")
    notes: str = Field(default="", description="备注说明，包括流转原因、历史背景")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ProvenanceTransferCreate(BaseModel):
    transfer_date: Optional[str] = Field(default=None)
    from_unit_id: Optional[str] = Field(default=None)
    to_unit_id: str = Field(description="转入收藏单位ID")
    transfer_type: str = Field(default="transfer")
    transferred_by: str = Field(default="")
    document_ref: str = Field(default="")
    access_number: str = Field(default="")
    condition_report: str = Field(default="")
    notes: str = Field(default="")


class ProvenanceTransferUpdate(BaseModel):
    transfer_date: Optional[str] = None
    from_unit_id: Optional[str] = None
    to_unit_id: Optional[str] = None
    transfer_type: Optional[str] = None
    transferred_by: Optional[str] = None
    document_ref: Optional[str] = None
    access_number: Optional[str] = None
    condition_report: Optional[str] = None
    notes: Optional[str] = None


class RepairRecord(BaseModel):
    id: Optional[str] = Field(default=None, description="修复记录唯一ID")
    leaf_id: str = Field(description="关联的叶片ID")
    repair_date: Optional[str] = Field(default=None, description="修复日期")
    performed_by: str = Field(default="", description="修复人员/机构")
    location: str = Field(default="", description="修复地点")
    repair_type: str = Field(default="conservation", description="修复类型：conservation(保护)/restoration(修复)/rebinding(重装)/digitization(数字化)/other")
    before_condition: str = Field(default="", description="修复前状况描述")
    after_condition: str = Field(default="", description="修复后状况描述")
    materials_used: str = Field(default="", description="使用的材料")
    techniques_used: str = Field(default="", description="使用的技术方法")
    treatment_report: str = Field(default="", description="详细处理报告")
    document_ref: str = Field(default="", description="修复档案编号")
    before_images: List[str] = Field(default_factory=list, description="修复前图片路径列表")
    after_images: List[str] = Field(default_factory=list, description="修复后图片路径列表")
    notes: str = Field(default="", description="备注")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class RepairRecordCreate(BaseModel):
    repair_date: Optional[str] = Field(default=None)
    performed_by: str = Field(default="")
    location: str = Field(default="")
    repair_type: str = Field(default="conservation")
    before_condition: str = Field(default="")
    after_condition: str = Field(default="")
    materials_used: str = Field(default="")
    techniques_used: str = Field(default="")
    treatment_report: str = Field(default="")
    document_ref: str = Field(default="")
    before_images: List[str] = Field(default_factory=list)
    after_images: List[str] = Field(default_factory=list)
    notes: str = Field(default="")


class RepairRecordUpdate(BaseModel):
    repair_date: Optional[str] = None
    performed_by: Optional[str] = None
    location: Optional[str] = None
    repair_type: Optional[str] = None
    before_condition: Optional[str] = None
    after_condition: Optional[str] = None
    materials_used: Optional[str] = None
    techniques_used: Optional[str] = None
    treatment_report: Optional[str] = None
    document_ref: Optional[str] = None
    before_images: Optional[List[str]] = None
    after_images: Optional[List[str]] = None
    notes: Optional[str] = None


class ResearchCitation(BaseModel):
    id: Optional[str] = Field(default=None, description="引用记录唯一ID")
    leaf_id: str = Field(description="关联的叶片ID")
    citation_type: str = Field(default="journal", description="引用类型：journal/book/conference/thesis/website/other")
    title: str = Field(description="文献标题")
    authors: List[str] = Field(default_factory=list, description="作者列表")
    year: Optional[int] = Field(default=None, description="出版年份")
    journal: str = Field(default="", description="期刊/出版物名称")
    volume: str = Field(default="", description="卷号")
    issue: str = Field(default="", description="期号")
    pages: str = Field(default="", description="页码范围")
    publisher: str = Field(default="", description="出版社")
    doi: str = Field(default="", description="DOI编号")
    url: str = Field(default="", description="在线链接")
    language: str = Field(default="zh", description="文献语言")
    cited_content: str = Field(default="", description="引用该叶片的具体内容/论述")
    cited_pages: str = Field(default="", description="引用内容在文献中的页码")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    significance: str = Field(default="", description="该引用对叶片研究的重要性说明")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ResearchCitationCreate(BaseModel):
    citation_type: str = Field(default="journal")
    title: str = Field(description="文献标题")
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = Field(default=None)
    journal: str = Field(default="")
    volume: str = Field(default="")
    issue: str = Field(default="")
    pages: str = Field(default="")
    publisher: str = Field(default="")
    doi: str = Field(default="")
    url: str = Field(default="")
    language: str = Field(default="zh")
    cited_content: str = Field(default="")
    cited_pages: str = Field(default="")
    keywords: List[str] = Field(default_factory=list)
    significance: str = Field(default="")


class ResearchCitationUpdate(BaseModel):
    citation_type: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    language: Optional[str] = None
    cited_content: Optional[str] = None
    cited_pages: Optional[str] = None
    keywords: Optional[List[str]] = None
    significance: Optional[str] = None


class TimelineEvent(BaseModel):
    event_id: str = Field(description="事件ID")
    event_type: str = Field(description="事件类型：discovery/transfer/repair/citation/associated_plan/consensus")
    event_date: Optional[str] = Field(default=None, description="事件日期")
    title: str = Field(description="事件标题")
    description: str = Field(default="", description="事件描述")
    location: Optional[str] = Field(default=None, description="事件发生地点")
    related_entity_id: Optional[str] = Field(default=None, description="关联实体ID（单位/方案/项目等）")
    related_entity_name: Optional[str] = Field(default=None, description="关联实体名称")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="额外数据")


class ProvenanceTimeline(BaseModel):
    leaf_id: str = Field(description="叶片ID")
    leaf_summary: Dict[str, Any] = Field(description="叶片基本信息摘要")
    events: List[TimelineEvent] = Field(description="按时间排序的事件列表")
    total_events: int = Field(description="事件总数")


class GraphNode(BaseModel):
    node_id: str = Field(description="节点唯一ID")
    node_type: str = Field(description="节点类型：leaf/site/unit/person/publication/plan")
    label: str = Field(description="节点显示标签")
    properties: Dict[str, Any] = Field(default_factory=dict, description="节点属性")


class GraphEdge(BaseModel):
    edge_id: str = Field(description="边唯一ID")
    source_id: str = Field(description="起始节点ID")
    target_id: str = Field(description="目标节点ID")
    relation_type: str = Field(description="关系类型：discovered_at/housed_at/transferred_to/repaired_by/cited_in/included_in/discussed_in")
    label: str = Field(default="", description="关系标签")
    date: Optional[str] = Field(default=None, description="关系日期")
    properties: Dict[str, Any] = Field(default_factory=dict, description="边属性")


class ProvenanceGraph(BaseModel):
    leaf_id: str = Field(description="中心叶片ID")
    nodes: List[GraphNode] = Field(description="图节点列表")
    edges: List[GraphEdge] = Field(description="图边列表")
    node_count: int = Field(description="节点总数")
    edge_count: int = Field(description="边总数")


class LeafProvenanceSummary(BaseModel):
    leaf_id: str = Field(description="叶片ID")
    discovery_site: Optional[DiscoverySite] = Field(default=None, description="发现地点信息")
    current_unit: Optional[CollectionUnit] = Field(default=None, description="当前收藏单位")
    transfer_count: int = Field(default=0, description="流转次数")
    repair_count: int = Field(default=0, description="修复次数")
    citation_count: int = Field(default=0, description="学术引用次数")
    associated_plans: List[Dict[str, Any]] = Field(default_factory=list, description="关联的复原方案列表")
    associated_projects: List[Dict[str, Any]] = Field(default_factory=list, description="关联的协同校勘项目列表")
    associated_annotations: List[Dict[str, Any]] = Field(default_factory=list, description="关联的图片标注摘要")
    consensus_summary: Optional[Dict[str, Any]] = Field(default=None, description="协同校勘共识摘要")
    source_reliability: float = Field(default=0.0, description="来源可靠性评分 0-1")
    completeness_score: float = Field(default=0.0, description="谱系信息完整度评分 0-1")


class RelatedLeavesQuery(BaseModel):
    by_site: Optional[bool] = Field(default=True, description="按发现地点关联")
    by_unit: Optional[bool] = Field(default=True, description="按收藏单位关联")
    by_transfer: Optional[bool] = Field(default=True, description="按流转路径关联")
    by_citation: Optional[bool] = Field(default=True, description="按学术引用关联")
    by_plan: Optional[bool] = Field(default=True, description="按复原方案关联")


class RelatedLeafInfo(BaseModel):
    leaf_id: str = Field(description="关联叶片ID")
    relation_type: str = Field(description="关联类型")
    relation_detail: str = Field(default="", description="关联详情")
    strength: float = Field(default=0.0, description="关联强度 0-1")


class TranscriptionWord(BaseModel):
    index: int = Field(description="词序号，从0开始")
    text: str = Field(description="词文本")
    normalized: str = Field(default="", description="标准化形式")
    uncertainty: float = Field(default=0.0, ge=0.0, le=1.0, description="识别不确定度 0-1")
    is_illegible: bool = Field(default=False, description="是否无法辨认")
    is_reconstructed: bool = Field(default=False, description="是否为推测补字")
    annotation_text: str = Field(default="", description="残文图片上对应区域标注文本")


class TranscriptionLine(BaseModel):
    line_number: int = Field(description="行号，从1开始")
    words: List[TranscriptionWord] = Field(default_factory=list, description="该行的词列表")
    annotation_text: str = Field(default="", description="整行原始转写文本")
    notes: str = Field(default="", description="行级注释")


class MultilingualTranscription(BaseModel):
    id: Optional[str] = Field(default=None, description="转写记录唯一ID")
    leaf_id: str = Field(description="关联的叶片ID")
    language: str = Field(description="语言代码：sa(梵文)/pi(巴利文)/bo(藏文)/zh(汉文)/other")
    language_label: str = Field(default="", description="语言显示名称，如：梵文、巴利文")
    script: str = Field(default="", description="书写系统：devanagari/sinhala/tibetan/chinese/romanized")
    lines: List[TranscriptionLine] = Field(default_factory=list, description="逐行转写内容")
    full_text: str = Field(default="", description="完整转写文本")
    transcription_type: str = Field(default="diplomatic", description="转写类型：diplomatic(实录)/normalized(标准化)/reconstructed(复原)")
    source: str = Field(default="", description="转写来源：manual(人工)/ocr(机器识别)/reference(引用文献)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="整体置信度")
    transcriber: str = Field(default="", description="转写者")
    reference: str = Field(default="", description="参考出处")
    linked_text_region_ids: List[str] = Field(default_factory=list, description="关联的图片残文区域ID列表")
    linked_damage_ids: List[str] = Field(default_factory=list, description="关联的破损区域ID列表")
    notes: str = Field(default="", description="备注")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class MultilingualTranscriptionCreate(BaseModel):
    language: str = Field(description="语言代码：sa/pi/bo/zh/other")
    language_label: str = Field(default="")
    script: str = Field(default="")
    lines: List[TranscriptionLine] = Field(default_factory=list)
    full_text: str = Field(default="")
    transcription_type: str = Field(default="diplomatic")
    source: str = Field(default="manual")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    transcriber: str = Field(default="")
    reference: str = Field(default="")
    linked_text_region_ids: List[str] = Field(default_factory=list)
    linked_damage_ids: List[str] = Field(default_factory=list)
    notes: str = Field(default="")


class MultilingualTranscriptionUpdate(BaseModel):
    language: Optional[str] = None
    language_label: Optional[str] = None
    script: Optional[str] = None
    lines: Optional[List[TranscriptionLine]] = None
    full_text: Optional[str] = None
    transcription_type: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    transcriber: Optional[str] = None
    reference: Optional[str] = None
    linked_text_region_ids: Optional[List[str]] = None
    linked_damage_ids: Optional[List[str]] = None
    notes: Optional[str] = None


class AlignmentPair(BaseModel):
    id: Optional[str] = Field(default=None, description="对齐对ID")
    leaf_id: str = Field(description="关联叶片ID")
    source_lang: str = Field(description="源语言代码")
    target_lang: str = Field(description="目标语言代码")
    source_text: str = Field(description="源语言文本片段")
    target_text: str = Field(description="目标语言文本片段")
    source_word_indices: List[int] = Field(default_factory=list, description="源语言词索引列表")
    target_word_indices: List[int] = Field(default_factory=list, description="目标语言词索引列表")
    source_line_number: Optional[int] = Field(default=None, description="源语言行号")
    target_line_number: Optional[int] = Field(default=None, description="目标语言行号")
    alignment_type: str = Field(default="word", description="对齐类型：word(逐词)/phrase(短语)/line(逐行)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="对齐置信度")
    is_disputed: bool = Field(default=False, description="是否存在对齐争议")
    notes: str = Field(default="", description="注释说明")
    created_by: str = Field(default="system", description="创建者")
    created_at: datetime = Field(default_factory=datetime.now)


class AlignmentPairCreate(BaseModel):
    source_lang: str
    target_lang: str
    source_text: str
    target_text: str
    source_word_indices: List[int] = Field(default_factory=list)
    target_word_indices: List[int] = Field(default_factory=list)
    source_line_number: Optional[int] = None
    target_line_number: Optional[int] = None
    alignment_type: str = Field(default="word")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_disputed: bool = Field(default=False)
    notes: str = Field(default="")
    created_by: str = Field(default="system")


class AlignmentPairUpdate(BaseModel):
    source_text: Optional[str] = None
    target_text: Optional[str] = None
    source_word_indices: Optional[List[int]] = None
    target_word_indices: Optional[List[int]] = None
    source_line_number: Optional[int] = None
    target_line_number: Optional[int] = None
    alignment_type: Optional[str] = None
    confidence: Optional[float] = None
    is_disputed: Optional[bool] = None
    notes: Optional[str] = None


class VariantAnnotation(BaseModel):
    id: Optional[str] = Field(default=None, description="异文标注ID")
    leaf_id: str = Field(description="关联叶片ID")
    variant_type: str = Field(description="异文类型：substitution(替换)/omission(缺文)/addition(增文)/transposition(倒文)/corruption(讹误)")
    language: str = Field(description="标注所属语言代码")
    position_description: str = Field(default="", description="异文位置描述")
    line_number: Optional[int] = Field(default=None, description="行号")
    word_indices: List[int] = Field(default_factory=list, description="涉及的词索引")
    original_text: str = Field(default="", description="原文/底本文字")
    variant_text: str = Field(default="", description="异文/变体文字")
    description: str = Field(default="", description="异文详细说明")
    significance: str = Field(default="", description="异文学术意义")
    source_edition: str = Field(default="", description="出处版本/校勘本")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    related_alignment_ids: List[str] = Field(default_factory=list, description="关联的对齐对ID")
    created_by: str = Field(default="system", description="标注者")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class VariantAnnotationCreate(BaseModel):
    variant_type: str
    language: str
    position_description: str = Field(default="")
    line_number: Optional[int] = None
    word_indices: List[int] = Field(default_factory=list)
    original_text: str = Field(default="")
    variant_text: str = Field(default="")
    description: str = Field(default="")
    significance: str = Field(default="")
    source_edition: str = Field(default="")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    related_alignment_ids: List[str] = Field(default_factory=list)
    created_by: str = Field(default="system")


class VariantAnnotationUpdate(BaseModel):
    variant_type: Optional[str] = None
    language: Optional[str] = None
    position_description: Optional[str] = None
    line_number: Optional[int] = None
    word_indices: Optional[List[int]] = None
    original_text: Optional[str] = None
    variant_text: Optional[str] = None
    description: Optional[str] = None
    significance: Optional[str] = None
    source_edition: Optional[str] = None
    confidence: Optional[float] = None
    related_alignment_ids: Optional[List[str]] = None


class TerminologyEntry(BaseModel):
    id: Optional[str] = Field(default=None, description="术语条目ID")
    term: str = Field(description="术语原文")
    language: str = Field(description="术语语言代码")
    translations: Dict[str, str] = Field(default_factory=dict, description="各语言译文 {language_code: translation}")
    sanskrit_root: str = Field(default="", description="梵文词根/语源")
    definition: str = Field(default="", description="术语定义/释义")
    category: str = Field(default="", description="术语分类：doctrine(教义)/ritual(仪轨)/philosophy(哲学)/grammar(文法)/other")
    references: List[str] = Field(default_factory=list, description="参考出处列表")
    related_terms: List[str] = Field(default_factory=list, description="关联术语ID列表")
    notes: str = Field(default="", description="备注")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TerminologyEntryCreate(BaseModel):
    term: str
    language: str
    translations: Dict[str, str] = Field(default_factory=dict)
    sanskrit_root: str = Field(default="")
    definition: str = Field(default="")
    category: str = Field(default="")
    references: List[str] = Field(default_factory=list)
    related_terms: List[str] = Field(default_factory=list)
    notes: str = Field(default="")


class TerminologyEntryUpdate(BaseModel):
    term: Optional[str] = None
    language: Optional[str] = None
    translations: Optional[Dict[str, str]] = None
    sanskrit_root: Optional[str] = None
    definition: Optional[str] = None
    category: Optional[str] = None
    references: Optional[List[str]] = None
    related_terms: Optional[List[str]] = None
    notes: Optional[str] = None


class RecognitionSuggestion(BaseModel):
    id: Optional[str] = Field(default=None, description="建议ID")
    leaf_id: str = Field(description="关联叶片ID")
    language: str = Field(description="目标语言代码")
    region_id: Optional[str] = Field(default=None, description="关联的图片残文区域ID")
    line_number: Optional[int] = Field(default=None, description="行号")
    word_index: Optional[int] = Field(default=None, description="词索引")
    suggested_text: str = Field(description="建议识别文本")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="置信度")
    alternatives: List[Dict[str, Any]] = Field(default_factory=list, description="备选方案 [{text, confidence}]")
    method: str = Field(default="pattern", description="识别方法：pattern(模式匹配)/dictionary(词典查找)/contextual(上下文推断)/manual(人工)")
    explanation: str = Field(default="", description="识别依据说明")
    is_accepted: Optional[bool] = Field(default=None, description="是否已被采纳：true/false/null(待定)")
    created_at: datetime = Field(default_factory=datetime.now)


class RecognitionSuggestionCreate(BaseModel):
    language: str
    region_id: Optional[str] = None
    line_number: Optional[int] = None
    word_index: Optional[int] = None
    suggested_text: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    method: str = Field(default="pattern")
    explanation: str = Field(default="")


class RecognitionSuggestionUpdate(BaseModel):
    suggested_text: Optional[str] = None
    confidence: Optional[float] = None
    alternatives: Optional[List[Dict[str, Any]]] = None
    method: Optional[str] = None
    explanation: Optional[str] = None
    is_accepted: Optional[bool] = None


class LeafMultilingualSummary(BaseModel):
    leaf_id: str = Field(description="叶片ID")
    transcriptions: List[MultilingualTranscription] = Field(default_factory=list, description="各语言转写列表")
    languages: List[str] = Field(default_factory=list, description="已有转写语言列表")
    alignment_count: int = Field(default=0, description="对齐对数量")
    variant_count: int = Field(default=0, description="异文标注数量")
    suggestion_count: int = Field(default=0, description="识别建议数量")
    pending_suggestions: int = Field(default=0, description="待处理建议数量")
    terminology_count: int = Field(default=0, description="关联术语数量")


class ComparativeReadingView(BaseModel):
    leaf_id: str = Field(description="叶片ID")
    leaf_info: Dict[str, Any] = Field(description="叶片基本信息")
    transcriptions_by_lang: Dict[str, MultilingualTranscription] = Field(default_factory=dict, description="按语言索引的转写")
    alignments: List[AlignmentPair] = Field(default_factory=list, description="对齐对列表")
    variants: List[VariantAnnotation] = Field(default_factory=list, description="异文标注列表")
    terminology: List[TerminologyEntry] = Field(default_factory=list, description="术语对照列表")
    suggestions: List[RecognitionSuggestion] = Field(default_factory=list, description="识别建议列表")
    plan_info: Optional[Dict[str, Any]] = Field(default=None, description="关联的复原方案信息")
    annotation_info: Optional[Dict[str, Any]] = Field(default=None, description="关联的图片标注信息")
    consensus_info: Optional[Dict[str, Any]] = Field(default=None, description="关联的协同校勘共识信息")
