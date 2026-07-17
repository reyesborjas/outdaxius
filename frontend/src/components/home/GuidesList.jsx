// frontend/src/components/home/GuidesList.jsx
import React from "react";
import useApiList from "./useApiList";

export default function GuidesList() {
  const { data, loading } = useApiList("/users?role=guide");

  if (loading) return <p className="text-muted">Loading…</p>;
  const guides = Array.isArray(data) ? data : [];

  return (
    <div className="row row-cols-1 row-cols-sm-2 row-cols-md-3 row-cols-lg-4 g-3">
      {guides.map((g) => (
        <div key={g.id} className="col">
          <div className="card h-100 text-center border-200 shadow-sm hover-shadow transition-all">
            <div className="card-body d-flex flex-column">
              <div className="mb-3">
                <img
                  src={g.profile?.avatar_url || g.profile_picture || "/placeholder-avatar.png"}
                  alt={g.display_name || g.first_name || "Guide"}
                  className="rounded-circle"
                  style={{ width: 80, height: 80, objectFit: "cover" }}
                />
              </div>
              
              <h5 className="fw-semibold mb-1">
                {g.display_name || [g.first_name, g.last_name].filter(Boolean).join(" ") || g.email}
              </h5>
              
              <div className="small text-muted mb-2">
                <span className="badge bg-primary">Guide</span>
              </div>

              {/* Company Info */}
              {g.company_name && (
                <div className="mt-2 mb-2">
                  <div className="small text-muted">Member of</div>
                  <div className="fw-semibold small">{g.company_name}</div>
                </div>
              )}

              {/* Profile Bio */}
              {g.profile?.about && (
                <p className="small text-muted text-truncate mt-auto">
                  {g.profile.about}
                </p>
              )}

              {/* Location if available */}
              {g.profile?.location && (
                <div className="small text-muted mt-2">
                  <i className="bi bi-geo-alt"></i> {g.profile.location}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
      {guides.length === 0 && <p className="text-muted mb-0">No guides found.</p>}
    </div>
  );
}