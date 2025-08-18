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
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Component(Base):
    __tablename__ = "components"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # type:name
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    org_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Blueprint(Base):
    __tablename__ = "blueprints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    body: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # frozen spec
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    org_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Execution(Base):
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

    events: Mapped[list[ExecutionEvent]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )  # type: ignore[name-defined]


class ExecutionEvent(Base):
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

    execution: Mapped[Execution] = relationship(back_populates="events")  # type: ignore[name-defined]


class Token(Base):
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


class VectorText(Text):  # simple marker for clarity; real pgvector set in migration
    pass


class SemanticMemory(Base):
    __tablename__ = "semantic_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(
        String(128), index=True
    )  # org/project/user/session
    key: Mapped[str] = mapped_column(String(256), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    vector: Mapped[Optional[str]] = mapped_column(
        VectorText, nullable=True
    )  # placeholder; real vector added via migration
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_semantic_scope_key", "scope", "key"),)
