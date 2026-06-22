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
    id: str = Field(description="流转记录唯一ID")
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
    leaf_id: str = Field(description="关联的叶片ID")
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
    id: str = Field(description="修复记录唯一ID")
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
    leaf_id: str = Field(description="关联的叶片ID")
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
    id: str = Field(description="引用记录唯一ID")
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
    leaf_id: str = Field(description="关联的叶片ID")
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
