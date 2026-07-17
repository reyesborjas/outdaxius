// ===============================
// src/components/home/ActivitiesGrid.jsx
// ===============================
import React, { useEffect, useMemo, useState } from "react";
import useApiList, { normalizeGallery } from "./useApiList";

export default function ActivitiesGrid({ asCarousel = false }) {
  const { data, loading } = useApiList("/activities");

  const items = useMemo(() => {
    const arr = Array.isArray(data) ? data : [];
    return arr.filter((a) => {
      const role = a?.creator?.role || a?.creator_role;
      return !role || role === "guide" || role === "admin";
    });
  }, [data]);

  // HOOKS ALWAYS
  const [idx, setIdx] = useState(0);
  const n = items.length;

  useEffect(() => {
    if (!asCarousel || !n) return;
    const t = setInterval(() => setIdx((i) => (i + 1) % n), 4000);
    return () => clearInterval(t);
  }, [asCarousel, n]);

  const coverOf = (a) => {
    const g = normalizeGallery(a?.gallery);
    return g.find((x) => x.position === 0)?.url || g[0]?.url;
  };

  if (loading) return <p className="text-muted">Loading…</p>;

  if (asCarousel) {
    if (!n) {
      return (
        <div className="ratio ratio-21x9 bg-body-tertiary rounded-3 d-flex align-items-center justify-content-center">
          <div className="text-muted">No activities available</div>
        </div>
      );
    }

    const left = (idx - 1 + n) % n;
    const right = (idx + 1) % n;
    const prev = () => setIdx((i) => (i - 1 + n) % n);
    const next = () => setIdx((i) => (i + 1) % n);

    return (
      <div className="position-relative">
        <div className="d-flex justify-content-center align-items-end gap-3">
          <img
            src={coverOf(items[left])}
            alt={items[left]?.title || "left"}
            onClick={prev}
            style={{ width: 220, height: 120, objectFit: "cover", borderRadius: 12, opacity: 0.85, cursor: "pointer" }}
          />
          <div className="position-relative">
            <img
              src={coverOf(items[idx])}
              alt={items[idx]?.title || "center"}
              style={{ width: "100%", maxWidth: 960, height: 200, objectFit: "cover", borderRadius: 16, boxShadow: "0 8px 24px rgba(0,0,0,0.25)" }}
            />
            <div
              className="position-absolute bottom-0 start-0 end-0 p-2 text-white"
              style={{ background: "linear-gradient(180deg,transparent,rgba(0,0,0,0.55))", borderBottomLeftRadius: 16, borderBottomRightRadius: 16 }}
            >
              <div className="fw-semibold text-truncate">{items[idx]?.title}</div>
              <div className="small text-truncate">
                {items[idx]?.location?.display_name || items[idx]?.activity_type || "Activity"}
              </div>
            </div>
          </div>
          <img
            src={coverOf(items[right])}
            alt={items[right]?.title || "right"}
            onClick={next}
            style={{ width: 220, height: 120, objectFit: "cover", borderRadius: 12, opacity: 0.85, cursor: "pointer" }}
          />
        </div>

        <button className="btn btn-light position-absolute top-50 start-0 translate-middle-y" onClick={prev} aria-label="Prev">
          ‹
        </button>
        <button className="btn btn-light position-absolute top-50 end-0 translate-middle-y" onClick={next} aria-label="Next">
          ›
        </button>
      </div>
    );
  }

  // Grid
  return (
    <div className="row row-cols-1 row-cols-sm-2 row-cols-md-3 g-3">
      {items.map((a) => (
        <div key={a.id} className="col">
          <div className="h-100 border rounded-3 bg-white shadow-sm overflow-hidden">
            {coverOf(a) && (
              <img src={coverOf(a)} alt={a.title || "activity"} style={{ width: "100%", height: 140, objectFit: "cover" }} />
            )}
            <div className="p-2">
              <div className="fw-semibold text-truncate">{a.title}</div>
              <div className="small text-muted text-truncate">
                {(a.activity.type?.type_name || "–")}
                {a.location?.display_name ? ` · ${a.location.display_name}` : ""}
              </div>
              <div className="small text-truncate" style={{ lineHeight: "1.25" }}>
                {a.description || "—"}
              </div>
            </div>
          </div>
        </div>
      ))}
      {items.length === 0 && <p className="text-muted mb-0">No activities found.</p>}
    </div>
  );
}
