"""Admin model with permissions (many-to-many)."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.admin_session import AdminSession
    from app.models.permission import Permission


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


admin_permissions = Table(
    "admin_permissions",
    Base.metadata,
    Column("admin_id", UUID(as_uuid=True), ForeignKey("admins.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary=admin_permissions, back_populates="admins", lazy="selectin"
    )
    sessions: Mapped[list["AdminSession"]] = relationship(
        "AdminSession", back_populates="admin", cascade="all, delete-orphan"
    )

    def has_permission(self, name: str) -> bool:
        if self.is_super_admin:
            return True
        return any(p.name == name for p in self.permissions)

    def permission_names(self) -> list[str]:
        return [p.name for p in self.permissions]
