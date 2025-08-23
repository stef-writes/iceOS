from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ComponentRecord(Base):
    __tablename__ = "components"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    org_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tags: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BlueprintRecord(Base):
    __tablename__ = "blueprints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    body: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    org_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tags: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ExecutionRecord(Base):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    blueprint_id: Mapped[str] = mapped_column(
        ForeignKey("blueprints.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[Optional[Any]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[Any]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cost_meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    events: Mapped[list[ExecutionEventRecord]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )  # type: ignore[name-defined]


class ExecutionEventRecord(Base):
    __tablename__ = "execution_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("executions.id"), nullable=False, index=True
    )
    node_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    ts: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    execution: Mapped[ExecutionRecord] = relationship(back_populates="events")  # type: ignore[name-defined]


class TokenRecord(Base):
    __tablename__ = "tokens"

    token_hash: Mapped[str] = mapped_column(String(255), primary_key=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scopes: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[Optional[Any]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SemanticMemoryRecord(Base):
    __tablename__ = "semantic_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(128), index=True)
    key: Mapped[str] = mapped_column(String(256), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    meta_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    org_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # The pgvector "embedding" column is created via Alembic migration. We avoid
    # declaring a SQLAlchemy field for it to keep ORM free of an extra type
    # dependency; repository functions use SQL text for inserts/queries.

    __table_args__ = (
        Index("ix_semantic_scope_key", "scope", "key"),
        Index("ix_semantic_org_scope", "org_id", "scope"),
        UniqueConstraint("org_id", "content_hash", name="uq_semantic_org_content_hash"),
    )
