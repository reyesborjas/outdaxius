import React from "react";
import useApiList from "./home/useApiList";

export default function LocationsList() {
  const { data, loading } = useApiList("/locations/");
  if (loading) return <p className="text-muted">Loading…</p>;

  const rows = Array.isArray(data) ? data : [];

  return (
    <>
      {/* Grid simple y accesible; integra tu mapa real si ya lo tienes */}
      <div className="row row-cols-2 row-cols-sm-3 row-cols-md-4 row-cols-lg-6 g-2">
        {rows.map((l) => (
          <div key={l.id} className="col">
            <div className="border rounded-3 p-2 h-100">
              <div className="fw-semibold text-truncate">{l.display_name || l.name}</div>
              <div className="small text-muted text-truncate">
                {[l.city, l.region, l.country].filter(Boolean).join(", ")}
              </div>
            </div>
          </div>
        ))}
        {rows.length === 0 && <p className="text-muted mb-0">No locations found.</p>}
      </div>
    </>
  );
}
