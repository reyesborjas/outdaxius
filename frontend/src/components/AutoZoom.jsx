// AutoZoom.jsx
import { useEffect, useMemo } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";

export default function AutoZoom({ points, onePointZoom = 14, maxZoomOnFit = 12 }) {
  const map = useMap();

  const validPts = useMemo(
    () => (points || []).filter(p =>
      Number.isFinite(p.lat) && Number.isFinite(p.lon)),
    [points]
  );

  useEffect(() => {
    if (!map || validPts.length === 0) return;

    if (validPts.length === 1) {
      const { lat, lon } = validPts[0];
      map.setView([lat, lon], onePointZoom, { animate: true });
      return;
    }

    const bounds = L.latLngBounds(validPts.map(({ lat, lon }) => [lat, lon]));
    // Evita ver “todo el mundo” y da margen visual
    map.fitBounds(bounds, {
      padding: [50, 50],
      maxZoom: maxZoomOnFit,
      animate: true,
    });
  }, [map, validPts, onePointZoom, maxZoomOnFit]);

  return null;
}
