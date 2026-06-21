from datetime import datetime
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator


class HolePosition(BaseModel):
    x: float = Field(description="穿孔 X 坐标（毫米）")
    y: float = Field(description="穿孔 Y 坐标（毫米）")

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


class Leaf(BaseModel):
    id: str = Field(description="叶片唯一编号，不能重复")
    length: float = Field(gt=0, description="叶片长度（毫米），必须大于 0")
    width: float = Field(gt=0, description="叶片宽度（毫米），必须大于 0")
    holes: List[HolePosition] = Field(default_factory=list, description="穿绳孔坐标列表")
    residual_text: str = Field(default="", description="残存文字内容")
    damage: str = Field(default="", description="破损情况描述")
    confirmed: bool = Field(default=False, description="是否已确认信息无误")
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


class LeafUpdate(BaseModel):
    length: Optional[float] = Field(default=None, gt=0)
    width: Optional[float] = Field(default=None, gt=0)
    holes: Optional[List[HolePosition]] = Field(default=None)
    residual_text: Optional[str] = Field(default=None)
    damage: Optional[str] = Field(default=None)
    confirmed: Optional[bool] = Field(default=None)


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
