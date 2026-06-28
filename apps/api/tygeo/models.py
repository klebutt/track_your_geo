from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tygeo.db import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    pilot_id: Mapped[str] = mapped_column(String(128), index=True)
    brand_name: Mapped[str] = mapped_column(String(512))
    location: Mapped[str] = mapped_column(String(512))
    model_name: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), default="completed")
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    visibility_rate: Mapped[float] = mapped_column(Float, default=0.0)
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)
    usage_log: Mapped[list | None] = mapped_column(JSON, nullable=True)

    query_results: Mapped[list["QueryResult"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="QueryResult.id",
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="Recommendation.id",
    )


class QueryResult(Base):
    __tablename__ = "query_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    query_text: Mapped[str] = mapped_column(Text)
    response_text: Mapped[str] = mapped_column(Text)
    brand_mentioned: Mapped[bool] = mapped_column(default=False)
    competitors_mentioned: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cited_domains: Mapped[list | None] = mapped_column(JSON, nullable=True)
    model_name: Mapped[str] = mapped_column(String(256), default="")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    sentiment: Mapped[str] = mapped_column(String(32), default="neutral")
    mention_position: Mapped[str] = mapped_column(String(32), default="not_mentioned")
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)

    run: Mapped["Run"] = relationship(back_populates="query_results")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    title: Mapped[str] = mapped_column(String(512))
    detail: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(128))

    run: Mapped["Run"] = relationship(back_populates="recommendations")
