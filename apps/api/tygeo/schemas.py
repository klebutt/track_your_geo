from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from tygeo.plain_report import PlainReportOut


class PilotSummary(BaseModel):
    id: str
    brand_name: str
    location: str
    query_count: int


class PilotDetail(PilotSummary):
    competitors: list[str]
    queries: list[str]
    seed_domains: list[str] = Field(default_factory=list)
    brand_domains: list[str] = Field(default_factory=list)


class CitedDomainOut(BaseModel):
    domain: str
    kind: Literal["brand_owned", "third_party"]


class RunCreate(BaseModel):
    pilot_id: str
    brand_name: str | None = None
    location: str | None = None


class RunFromUrlCreate(BaseModel):
    url: str
    vertical: str = "accountants"


class QueryResultOut(BaseModel):
    id: int
    query_text: str
    response_text: str
    brand_mentioned: bool
    competitors_mentioned: dict[str, bool] | None
    cited_domains: list[CitedDomainOut] = Field(default_factory=list)
    model_name: str = ""
    latency_ms: float
    cost_usd: float
    sentiment: str = "neutral"
    mention_position: str = "not_mentioned"
    relevance_score: float = 0.0

    @field_validator("cited_domains", mode="before")
    @classmethod
    def _coerce_cited_domains(cls, value: object) -> object:
        return value or []

    model_config = {"from_attributes": True}


class RecommendationOut(BaseModel):
    id: int
    title: str
    detail: str
    impact: str
    category: str

    model_config = {"from_attributes": True}


class RunOut(BaseModel):
    id: int
    created_at: datetime
    pilot_id: str
    brand_name: str
    location: str
    model_name: str
    status: str
    total_cost_usd: float
    total_prompt_tokens: int
    total_completion_tokens: int
    visibility_rate: float
    composite_score: float
    query_results: list[QueryResultOut]
    recommendations: list[RecommendationOut]
    usage_log: list[dict[str, Any]] | None = None
    source_url: str | None = None
    profile_snapshot: dict[str, Any] | None = None
    plain_report: PlainReportOut | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _attach_plain_report(self) -> Self:
        from tygeo.plain_report import build_plain_report

        snap = self.profile_snapshot or {}
        self.plain_report = build_plain_report(
            status=self.status,
            brand_name=self.brand_name,
            model_name=self.model_name,
            query_results=self.query_results,
            locality_stance=str(snap.get("locality_stance") or "") or None,
            location=str(snap.get("location") or self.location or "") or None,
        )
        return self


class RunListItem(BaseModel):
    id: int
    created_at: datetime
    pilot_id: str
    brand_name: str
    status: str
    visibility_rate: float
    total_cost_usd: float
    source_url: str | None = None

    model_config = {"from_attributes": True}
