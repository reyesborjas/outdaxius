# app/schemas/location.py
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, HttpUrl

class LocationResolveIn(BaseModel):
    display_name: Optional[str] = None
    google_maps_url: Optional[HttpUrl] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

class LocationOut(BaseModel):
    id: UUID
    display_name: str
    lat: float
    lon: float
    plus_code: Optional[str] = None
    google_maps_url: Optional[str] = None
    source: Optional[str] = None
    osm_id: Optional[int] = None
    geonames_id: Optional[int] = None
    wof_id: Optional[int] = None
    wikidata_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
