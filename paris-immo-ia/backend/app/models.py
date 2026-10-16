"""Miroir SQLAlchemy des tables définies dans frontend/prisma/schema.prisma.

Prisma reste propriétaire des migrations ; ces classes ne créent rien en
production (seuls les tests appellent Base.metadata.create_all sur SQLite).
La table `photos` n'est utilisée que par Next.js et n'a pas de miroir ici.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    # Prisma stocke des TIMESTAMP(3) sans fuseau, en UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(str, enum.Enum):
    TENANT = "TENANT"
    LANDLORD = "LANDLORD"


class PropertyStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RENTED = "RENTED"


class DPE(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"


def _pg_enum(cls: type[enum.Enum], name: str) -> Enum:
    # Les types enum Postgres sont créés par Prisma sous le nom du enum Prisma.
    return Enum(cls, name=name, create_type=False, values_callable=lambda e: [m.value for m in e])


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str | None] = mapped_column(String)
    role: Mapped[Role] = mapped_column(_pg_enum(Role, "Role"), default=Role.TENANT)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    properties: Mapped[list["Property"]] = relationship(back_populates="owner")
    alerts: Mapped[list["SearchAlert"]] = relationship(back_populates="user")


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[PropertyStatus] = mapped_column(
        _pg_enum(PropertyStatus, "PropertyStatus"), default=PropertyStatus.ACTIVE
    )

    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String)
    quartier: Mapped[str] = mapped_column(String)
    arrondissement: Mapped[int] = mapped_column(Integer)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)

    rent_hc: Mapped[int] = mapped_column(Integer)
    charges: Mapped[int] = mapped_column(Integer, default=0)
    surface: Mapped[float] = mapped_column(Float)
    rooms: Mapped[int] = mapped_column(Integer)
    bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    floor: Mapped[int] = mapped_column(Integer, default=0)
    has_elevator: Mapped[bool] = mapped_column(Boolean, default=False)
    furnished: Mapped[bool] = mapped_column(Boolean, default=False)
    dpe: Mapped[DPE] = mapped_column(_pg_enum(DPE, "DPE"))

    has_fiber: Mapped[bool] = mapped_column(Boolean, default=False)
    faces_courtyard: Mapped[bool] = mapped_column(Boolean, default=False)
    has_balcony: Mapped[bool] = mapped_column(Boolean, default=False)
    has_parking: Mapped[bool] = mapped_column(Boolean, default=False)
    has_cellar: Mapped[bool] = mapped_column(Boolean, default=False)
    has_dishwasher: Mapped[bool] = mapped_column(Boolean, default=False)
    pets_allowed: Mapped[bool] = mapped_column(Boolean, default=False)

    photos: Mapped[list] = mapped_column(JSON, default=list)
    available_from: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    owner: Mapped[User] = relationship(back_populates="properties")

    @property
    def rent_cc(self) -> int:
        return self.rent_hc + self.charges


class SearchAlert(Base):
    __tablename__ = "search_alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    criteria: Mapped[dict] = mapped_column(JSON)
    query: Mapped[str] = mapped_column(String)
    min_score: Mapped[int] = mapped_column(Integer, default=90)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped[User] = relationship(back_populates="alerts")
