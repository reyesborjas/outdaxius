# app/models/user.py
from sqlalchemy import Boolean, Column, Date, DateTime, String, text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base  # or your Base
import uuid
import enum
from sqlalchemy.orm import relationship


class UserRole(enum.Enum):
    # Matches the live Postgres user_role enum (Phase 2 migration renamed the old
    # "user"/"company" labels to "client"/"guide") -- this Python enum had drifted out of sync
    # with that rename until now, so GET /roles/ and POST /roles/assign were both silently
    # advertising/accepting two role strings ("user", "company") the database has never held.
    client = "client"
    guide = "guide"
    admin = "admin"
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # NEW mapped columns (exist in DB)
    tax_id = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    national_id = Column(String, nullable=True)
    passport_number = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)
    fiscal_data = Column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    profile = Column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    preferred_language = Column(String(5), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    role = Column(String(50), nullable=False)

    birth_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    created_activities = relationship(
        "Activity",
        foreign_keys="Activity.created_by",
        back_populates="creator",
        cascade="all, delete-orphan"
    )
    led_activities = relationship(
        "Activity",
        foreign_keys="Activity.guide_leader",
        back_populates="leader"
    )
    
    created_programs = relationship(
        "Program",
        foreign_keys="Program.created_by",
        back_populates="creator",
        cascade="all, delete-orphan"
    )
    led_programs = relationship(
        "Program",
        foreign_keys="Program.guide_leader",
        back_populates="leader"
    )



