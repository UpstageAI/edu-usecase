from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class DocumentStatus(str, enum.Enum):
    """Workflow status for an uploaded document."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extension: Mapped[str | None] = mapped_column(String(20), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    pages_count: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    selection_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    mermaid_chart: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_strategy: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recommendation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_strategy: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ocr_speed_ms_per_page: Mapped[float | None] = mapped_column(Float, nullable=True)
    benchmark_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentPage.page_number"
    )
    analysis_items: Mapped[list["AnalysisItem"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="AnalysisItem.page_number"
    )
    page_provider_results: Mapped[list["PageOcrResult"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="PageOcrResult.page_number",
    )
    report_agent_statuses: Mapped[list["ReportAgentStatus"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number", name="uix_document_page"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    page_number: Mapped[int] = mapped_column(Integer)
    text_content: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document: Mapped[Document] = relationship(back_populates="pages")
    provider_results: Mapped[list["PageOcrResult"]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="PageOcrResult.provider",
    )


class AnalysisItem(Base):
    __tablename__ = "analysis_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    context_type: Mapped[str] = mapped_column(String(64), default="paragraph")
    confidence: Mapped[float] = mapped_column(Float)
    page_number: Mapped[int] = mapped_column(Integer)

    document: Mapped[Document] = relationship(back_populates="analysis_items")


class PageOcrResult(Base):
    __tablename__ = "page_ocr_results"
    __table_args__ = (UniqueConstraint("document_id", "page_number", "provider", name="uix_page_provider"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    document_page_id: Mapped[int] = mapped_column(ForeignKey("document_pages.id", ondelete="CASCADE"))
    page_number: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(128))
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    validity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    llm_judge_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_per_page: Mapped[float | None] = mapped_column(Float, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document: Mapped[Document] = relationship(back_populates="page_provider_results")
    page: Mapped[DocumentPage] = relationship(back_populates="provider_results")


class AgentStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportAgentStatus(Base):
    __tablename__ = "report_agent_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    agent_name: Mapped[str] = mapped_column(String(64))
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped[Document] = relationship(back_populates="report_agent_statuses")
