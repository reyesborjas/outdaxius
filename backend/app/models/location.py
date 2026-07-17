# app/models/location.py
from sqlalchemy import Column, String, Float, TIMESTAMP, func, BigInteger
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base  # ajusta a tu base
from sqlalchemy.orm import relationship

class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)

    # Campos nuevos
    source = Column(String(16), nullable=False, default="manual")  # 'osm|geonames|wof|wikidata|manual'
    osm_id = Column(BigInteger, nullable=True)
    geonames_id = Column(BigInteger, nullable=True)
    wof_id = Column(BigInteger, nullable=True)
    wikidata_id = Column(String, nullable=True)

    google_maps_url = Column(String, nullable=True)

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    activities = relationship(
            "Activity",
            back_populates="location",
            cascade="all, delete-orphan",
            passive_deletes=True,
        )