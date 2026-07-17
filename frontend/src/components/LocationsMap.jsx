import React, { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import AutoZoom from "./AutoZoom";
import L from "leaflet";

const API = import.meta.env.VITE_API || "http://127.0.0.1:8000/api";

const icon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

export default function LocationsMap() {
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    fetch(`${API}/locations`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((j) => alive && setLocations(Array.isArray(j) ? j : []))
      .catch(() => alive && setLocations([]))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, []);

  const markers = useMemo(() => {
    return (locations || []).filter(
      (l) => Number.isFinite(l.lat) && Number.isFinite(l.lon)
    );
  }, [locations]);

  const center = markers.length ? [markers[0].lat, markers[0].lon] : [0, 0];

  return (
    <div className="w-100 rounded-3 overflow-hidden border" style={{ height: 420 }}>
      {loading ? (
        <div className="h-100 d-flex align-items-center justify-content-center text-muted">
          Loading map…
        </div>
      ) : (
        <MapContainer
          center={center}
          zoom={3}
          scrollWheelZoom={true}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {markers.map((m) => (
            <Marker key={m.id} position={[m.lat, m.lon]} icon={icon}>
              <Popup>
                <div className="fw-semibold mb-1">{m.display_name}</div>
                {m.google_maps_url && (
                  <a
                    href={m.google_maps_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="small"
                  >
                    View on Google Maps
                  </a>
                )}
              </Popup>
            </Marker>
          ))}
          <AutoZoom
            points={markers.map((m) => ({ lat: m.lat, lon: m.lon }))}
            onePointZoom={14}
            maxZoomOnFit={10}
          />
        </MapContainer>
      )}
    </div>
  );
}
