from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


Category = Literal["社会民生", "科技互联网", "商业财经", "公共政策", "文娱体育", "其他"]
AttentionLevel = Literal["high", "medium", "low"]
HotspotStatus = Literal["pending", "tracking", "archived"]


class HotspotCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=4, max_length=150)
    content_excerpt: str = Field(min_length=8, max_length=5000)
    source_platform: str = Field(default="", max_length=80)
    source_url: Optional[HttpUrl] = None
    published_at: Optional[datetime] = None
    engagement_count: Optional[int] = Field(default=None, ge=0)


class HotspotStatusUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    status: HotspotStatus
    note: str = Field(default="", max_length=300)


class AnalysisRun(BaseModel):
    expected_version: int = Field(ge=1)
    mode: Literal["deepseek", "rules"] = "deepseek"


class AnalysisEdit(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    expected_version: int = Field(ge=1)
    category: Optional[Category] = None
    attention_level: Optional[AttentionLevel] = None
    summary: Optional[str] = Field(default=None, min_length=4, max_length=500)
    keywords: Optional[List[str]] = Field(default=None, max_length=10)
    entities: Optional[List[str]] = Field(default=None, max_length=10)
    can_auto_handle: Optional[bool] = None
    action_suggestion: Optional[str] = Field(default=None, min_length=4, max_length=1000)
    missing_information: Optional[List[str]] = Field(default=None, max_length=10)
    review_note: str = Field(default="", max_length=300)

    @model_validator(mode="after")
    def require_change(self):
        fields = ("category", "attention_level", "summary", "keywords", "entities",
                  "can_auto_handle", "action_suggestion", "missing_information")
        if all(getattr(self, name) is None for name in fields):
            raise ValueError("至少需要修改一个分析字段")
        return self


class AnalysisConfirm(BaseModel):
    expected_version: int = Field(ge=1)
    review_note: str = Field(default="", max_length=300)
