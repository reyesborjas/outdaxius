# backend/app/api/locations.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from pydantic import BaseModel
import re
import requests

from app.db.session import get_db
from app.models.location import Location
from app.schemas.location import LocationOut, LocationResolveIn

router = APIRouter()
UA = {"User-Agent": "outdaxius/1.0 (support@outdaxius.local)"}
NOMINATIM = "https://nominatim.openstreetmap.org"

# ---------- Inbound models (local, sin depender de schemas pydantic globales) ----------
class LocationCreateIn(BaseModel):
    display_name: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    plus_code: Optional[str] = None
    google_maps_url: Optional[str] = None

class LocationUpsertByName(BaseModel):
    display_name: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    plus_code: Optional[str] = None
    google_maps_url: Optional[str] = None

# ---------- Helpers ----------
def _strip_lower(s: Optional[str]) -> str:
    return (s or "").strip().lower()

def _extract_latlon_from_gmaps(url: str) -> Tuple[Optional[float], Optional[float]]:
    try:
        u = urlparse(url)
        m = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+),", u.path)
        if m:
            return float(m.group(1)), float(m.group(2))
        q = parse_qs(u.query).get("q", [])
        if q:
            parts = q[0].split(",")
            if len(parts) >= 2:
                return float(parts[0]), float(parts[1])
    except Exception:
        pass
    return None, None

def _nominatim_search(name: str):
    r = requests.get(
        f"{NOMINATIM}/search",
        params={"q": name, "format": "jsonv2", "limit": 1},
        headers=UA, timeout=10,
    )
    r.raise_for_status()
    js = r.json()
    return js[0] if js else None

def _nominatim_reverse(lat: float, lon: float):
    r = requests.get(
        f"{NOMINATIM}/reverse",
        params={"lat": lat, "lon": lon, "format": "jsonv2"},
        headers=UA, timeout=10,
    )
    r.raise_for_status()
    return r.json()

def _nearby(db: Session, name: Optional[str], lat: Optional[float], lon: Optional[float]) -> Optional[Location]:
    tol = 0.00055  # ~60 m
    if name:
        by_name = db.query(Location).filter(func.lower(Location.display_name) == name.lower()).first()
        if by_name:
            return by_name
    if lat is not None and lon is not None:
        return db.query(Location).filter(
            Location.lat.between(lat - tol, lat + tol),
            Location.lon.between(lon - tol, lon + tol),
        ).first()
    return None

def _upsert_location(db: Session, *, name: str, lat: float, lon: float,
                     source: str, gmaps: Optional[str], osm_id: Optional[int]) -> Location:
    found = _nearby(db, name, lat, lon)
    if found:
        changed = False
        if gmaps and not found.google_maps_url:
            found.google_maps_url = gmaps; changed = True
        if osm_id and not found.osm_id:
            found.osm_id = osm_id; changed = True
        if source and found.source == "manual":
            found.source = source; changed = True
        if changed:
            db.flush()
        return found
    loc = Location(
        display_name=name, lat=lat, lon=lon,
        source=source, osm_id=osm_id, google_maps_url=gmaps
    )
    db.add(loc); db.flush()
    return loc

# ---------- Endpoints ----------
@router.get("/", response_model=List[LocationOut])
def list_locations(db: Session = Depends(get_db)):
    return db.query(Location).order_by(Location.display_name.asc()).all()

@router.get("/search", response_model=List[LocationOut])
def search_locations(q: str = Query(..., min_length=2), db: Session = Depends(get_db)):
    qn = f"%{_strip_lower(q)}%"
    return (
        db.query(Location)
        .filter(func.lower(Location.display_name).like(qn))
        .order_by(Location.display_name.asc())
        .limit(50)
        .all()
    )

@router.post("/", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_location(payload: LocationCreateIn, db: Session = Depends(get_db)):
    name = (payload.display_name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="display_name is required")

    # dedupe por nombre
    existing = (
        db.query(Location)
        .filter(func.lower(Location.display_name) == name.lower())
        .first()
    )
    # dedupe por lat/lon/url si vienen
    if not existing and (payload.lat is not None and payload.lon is not None):
        existing = _nearby(db, None, float(payload.lat), float(payload.lon))
    if not existing and payload.google_maps_url:
        existing = (
            db.query(Location)
            .filter(Location.google_maps_url == payload.google_maps_url)
            .first()
        )

    if existing:
        raise HTTPException(status_code=400, detail="Location already exists")

    loc = Location(
        display_name=name,
        lat=float(payload.lat) if payload.lat is not None else 0.0,
        lon=float(payload.lon) if payload.lon is not None else 0.0,
        google_maps_url=payload.google_maps_url,
        # plus_code se mantiene si tu modelo lo tiene; si no, ignora
        # plus_code=payload.plus_code,
        source="manual",
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc

@router.post("/upsert-by-name", response_model=LocationOut)
def upsert_location_by_name(payload: LocationUpsertByName, db: Session = Depends(get_db)):
    name = (payload.display_name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="display_name is required")

    loc = (
        db.query(Location)
        .filter(func.lower(Location.display_name) == name.lower())
        .first()
    )
    if loc:
        changed = False
        if payload.lat is not None and (loc.lat is None or loc.lat == 0):
            loc.lat = float(payload.lat); changed = True
        if payload.lon is not None and (loc.lon is None or loc.lon == 0):
            loc.lon = float(payload.lon); changed = True
        if payload.google_maps_url and not loc.google_maps_url:
            loc.google_maps_url = payload.google_maps_url; changed = True
        # if payload.plus_code and not loc.plus_code: loc.plus_code = payload.plus_code; changed = True
        if changed:
            db.commit(); db.refresh(loc)
        return loc

    loc = Location(
        display_name=name,
        lat=float(payload.lat) if payload.lat is not None else 0.0,
        lon=float(payload.lon) if payload.lon is not None else 0.0,
        google_maps_url=payload.google_maps_url,
        # plus_code=payload.plus_code,
        source="manual",
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc

@router.post("/resolve", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def resolve_location(payload: LocationResolveIn, db: Session = Depends(get_db)):
    name = (payload.display_name or "").strip() or None
    lat, lon = payload.lat, payload.lon
    gmaps = payload.google_maps_url

    if (lat is None or lon is None) and gmaps:
        glat, glon = _extract_latlon_from_gmaps(gmaps)
        lat = lat or glat
        lon = lon or glon

    osm_id = None
    source = "manual"

    if (lat is None or lon is None) and name:
        hit = _nominatim_search(name)
        if hit:
            lat = float(hit["lat"]); lon = float(hit["lon"])
            osm_id = int(hit.get("osm_id") or 0) or None
            name = hit.get("display_name") or name
            source = "osm"

    if name is None and (lat is not None and lon is not None):
        rev = _nominatim_reverse(lat, lon)
        disp = rev.get("display_name")
        osm_id = int(rev.get("osm_id") or 0) or None
        name = disp or f"{lat},{lon}"
        source = "osm" if disp else "manual"

    if name is None or lat is None or lon is None:
        raise HTTPException(status_code=422, detail="Insufficient location data")

    loc = _upsert_location(db, name=name, lat=float(lat), lon=float(lon),
                           source=source, gmaps=gmaps, osm_id=osm_id)
    db.commit(); db.refresh(loc)
    return loc
