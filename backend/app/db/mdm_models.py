"""MDM catalog tables — simulates upstream product master until MDM exposes an API."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class MdmService(Base):
    __tablename__ = "mdm_services"
    __table_args__ = (
        UniqueConstraint("sku", "category_id", name="uq_mdm_services_sku_category"),
        Index("idx_mdm_services_category", "category_id"),
        Index("idx_mdm_services_group", "category_id", "service_group"),
        Index("idx_mdm_services_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku: Mapped[str] = mapped_column(String(128), nullable=False)
    category_id: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str] = mapped_column(String(16), nullable=False)
    bu: Mapped[str] = mapped_column(String(64), nullable=False)
    department_team: Mapped[str | None] = mapped_column(String(64))
    service_group: Mapped[str | None] = mapped_column(String(64))
    service_group_display: Mapped[str | None] = mapped_column(String(128))
    product_name: Mapped[str] = mapped_column(Text, nullable=False)
    service_name_on_proposal: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    scope_of_work: Mapped[str | None] = mapped_column(Text)
    service_type: Mapped[str] = mapped_column(String(32), nullable=False)
    billing_frequency: Mapped[str] = mapped_column(String(16), nullable=False)
    recurring: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="ACTIVE")
    pricing_type: Mapped[str] = mapped_column(String(32), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    price_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    price_spec: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    fee_raw: Mapped[str | None] = mapped_column(Text)
    footnotes: Mapped[str | None] = mapped_column(Text)
    sku_semantic_for_ai: Mapped[str | None] = mapped_column(Text)
    external_record_id: Mapped[str | None] = mapped_column(String(64))
    source_sheet: Mapped[str | None] = mapped_column(String(64))
    source_row: Mapped[int | None] = mapped_column(Integer)
    extensions: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    package_links: Mapped[list["MdmPackageService"]] = relationship(back_populates="service")


class MdmPackage(Base):
    __tablename__ = "mdm_packages"
    __table_args__ = (Index("idx_mdm_packages_category", "category_id"),)

    package_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category_id: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str] = mapped_column(String(16), nullable=False)
    bu: Mapped[str] = mapped_column(String(64), nullable=False)
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    package_detail: Mapped[str | None] = mapped_column(Text)
    package_semantic_for_ai: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    service_links: Mapped[list["MdmPackageService"]] = relationship(
        back_populates="package", cascade="all, delete-orphan"
    )


class MdmPackageService(Base):
    __tablename__ = "mdm_package_services"

    package_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("mdm_packages.package_id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sku: Mapped[str] = mapped_column(String(128), primary_key=True)
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mdm_services.id", ondelete="SET NULL"), nullable=True
    )

    package: Mapped["MdmPackage"] = relationship(back_populates="service_links")
    service: Mapped["MdmService | None"] = relationship(back_populates="package_links")


class MdmPackageNameAlias(Base):
    __tablename__ = "mdm_package_name_aliases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region: Mapped[str] = mapped_column(String(16), nullable=False, server_default="AU")
    legacy_name: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
