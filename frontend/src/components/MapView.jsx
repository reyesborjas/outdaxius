import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import AutoFitBounds from "./AutoFitBounds";

export default function MapView({ points }) {
  const valid = (points || []).filter(p => Number.isFinite(p.lat) && Number.isFinite(p.lon));
  return (
    <MapContainer center={[0, 0]} zoom={2} style={{ height: 500 }}>
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {valid.map((p, i) => (
        <Marker key={i} position={[p.lat, p.lon]}>
          <Popup>{p.display_name || p.name}</Popup>
        </Marker>
      ))}
      <AutoFitBounds points={valid} />
    </MapContainer>
  );
}
