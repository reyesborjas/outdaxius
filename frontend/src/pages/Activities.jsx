// frontend/src/pages/Activities.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useLocation, useNavigate } from "react-router-dom";
import EditActivityModal from "./EditActivityModal";
import ViewActivityModal from "./ViewActivityModal";
import SearchBar from "../components/SearchBar";

const API = import.meta.env.VITE_API || "http://127.0.0.1:8000/api";

function normalizeGallery(g) {
  if (!Array.isArray(g)) return [];
  return g
    .map((it, i) => {
      if (typeof it === "string") return { url: it, tag: "", position: i };
      const pos = Number.isFinite(Number(it?.position)) ? Number(it.position) : i;
      return { url: it?.url, tag: it?.tag || "", position: pos };
    })
    .filter((x) => !!x.url)
    .sort((a, b) => a.position - b.position);
}
function coverOf(gallery) {
  const arr = normalizeGallery(gallery);
  if (!arr.length) return null;
  return arr.find((x) => x.position === 0) || arr[0];
}

export default function Activities() {
  const { user, token, loading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const inDashboard = location.pathname.startsWith("/main/");
  const dashBase = useMemo(
    () => (user?.email ? `/main/${encodeURIComponent(user.email)}` : "/main"),
    [user?.email]
  );

  const [all, setAll] = useState([]);
  const [list, setList] = useState([]);
  const [scheduleCounts, setScheduleCounts] = useState({});

  const [q, setQ] = useState("");
  const [scope, setScope] = useState("all"); // all | activity | location | program
  const [searching, setSearching] = useState(false);

  const [selected, setSelected] = useState(null);
  const [mode, setMode] = useState(null); // "edit" | "view"

  useEffect(() => {
    let alive = true;
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    fetch(`${API}/activities/`, { headers })
      .then((r) => (r.ok ? r.json() : []))
      .then((rows) => {
        if (!alive) return;
        const data = (Array.isArray(rows) ? rows : []).map((a) => ({
          ...a,
          gallery: normalizeGallery(a.gallery),
        }));
        setAll(data);
        setList([...data].sort((a, b) => a.title.localeCompare(b.title)));
      })
      .catch(() => {
        if (!alive) return;
        setAll([]);
        setList([]);
      });
    return () => {
      alive = false;
    };
  }, [token]);

  // Bulk-fetch schedules once so each card can show an "N upcoming" badge without an N+1
  // request-per-card. Public/unscoped on purpose -- this is the customer-facing browse view.
  useEffect(() => {
    let alive = true;
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    fetch(`${API}/activity-schedules/`, { headers })
      .then((r) => (r.ok ? r.json() : []))
      .then((rows) => {
        if (!alive) return;
        const now = Date.now();
        const counts = {};
        (Array.isArray(rows) ? rows : []).forEach((s) => {
          if (!s.activity_id) return;
          if (s.start_time && new Date(s.start_time).getTime() < now) return;
          counts[s.activity_id] = (counts[s.activity_id] || 0) + 1;
        });
        setScheduleCounts(counts);
      })
      .catch(() => {
        if (!alive) return;
        setScheduleCounts({});
      });
    return () => {
      alive = false;
    };
  }, [token]);

  const canEdit = (a) => {
    if (!inDashboard || !user) return false;
    if (user.role === "admin") return true;
    const isOwner =
      (a?.creator?.id && a.creator.id === user.id) ||
      (a?.creator_id && a.creator_id === user.id) ||
      (a?.created_by && a.created_by === user.id) ||
      (a?.creator?.email && a.creator.email === user.email);
    return user.role === "guide" && isOwner;
  };

  const upsertActivity = (item) =>
    setList((xs) => {
      const cleaned = { ...item, gallery: normalizeGallery(item.gallery) };
      const has = xs.some((a) => a.id === item.id);
      const arr = has ? xs.map((a) => (a.id === item.id ? cleaned : a)) : [...xs, cleaned];
      return [...arr].sort((a, b) => a.title.localeCompare(b.title));
    });
  const removeActivity = (id) => setList((xs) => xs.filter((a) => a.id !== id));

  const clearSearch = () => {
    setQ("");
    setScope("all");
    setList([...all].sort((a, b) => a.title.localeCompare(b.title)));
  };

const runSearch = async ({ query }) => {
  const text = (query || "").trim().toLowerCase();
  if (!text || text.length < 2) {
    clearSearch();
    return;
  }

  setSearching(true);
  try {
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const r = await fetch(
      `${API}/activities/search?q=${encodeURIComponent(text)}`,
      { headers }
    );
    const arr = r.ok ? await r.json() : [];
    const normalized = arr.map(a => ({
      ...a,
      gallery: normalizeGallery(a.gallery)
    }));
    setList(normalized.sort((a, b) => a.title.localeCompare(b.title)));
  } catch (error) {
    console.error("Search error:", error);
    setList([]);
  } finally {
    setSearching(false);
  }
};


  if (loading) return null;

  return (
    <div className="min-vh-100 d-flex flex-column bg-surface-light">
      <main className="flex-grow-1 container-lg px-3 py-4">
        <div className="d-flex flex-wrap gap-2 justify-content-between align-items-center mb-3">
          

          <SearchBar
            value={q}
            scope={scope}
            onChange={setQ}
            onScopeChange={setScope}
            onSearch={runSearch}
            onClear={clearSearch}
            loading={searching}
            placeholder="Search activities… (title, type, location or program name)"
            className="flex-grow-1"
          />

          {inDashboard && user && (user.role === "admin" || user.role === "guide") && (
            <button
              onClick={() => navigate(`${dashBase}/create-activity`)}
              className="btn btn-primary ms-auto"
              type="button"
            >
              + New Activity
            </button>
          )}
        </div>

        <div className="row row-cols-1 row-cols-sm-2 row-cols-lg-3 g-3">
          {list.map((a) => {
            const cover = coverOf(a.gallery);
            return (
              <div key={a.id} className="col">
                <div
                  className="position-relative border rounded p-card bg-surface-snow shadow-card h-100 cursor-pointer"
                  onClick={() => {
                    if (!inDashboard) {
                      setSelected(a);
                      setMode("view");
                    }
                  }}
                >
                  {cover && (
                    <img
                      src={cover.url}
                      alt={cover.tag || a.title}
                      className="w-100 rounded mb-2"
                      style={{ height: "160px", objectFit: "cover" }}
                    />
                  )}

                  {inDashboard && canEdit(a) && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelected(a);
                        setMode("edit");
                      }}
                      className="btn btn-light btn-sm position-absolute top-0 start-0 m-2 shadow-card rounded-circle"
                      title="Edit activity"
                      type="button"
                    >
                      ✎
                    </button>
                  )}

                  {inDashboard && user && !canEdit(a) && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelected(a);
                        setMode("view");
                      }}
                      className="btn btn-light btn-sm position-absolute top-0 start-50 translate-middle-x m-2 shadow-card rounded-circle"
                      title="View activity"
                      type="button"
                    >
                      👁
                    </button>
                  )}

                  <h3 className="fw-bold mb-1">{a.title}</h3>
                  <div className="small text-muted">
                    {(a.type?.type_name || "–")}
                    {a.location?.display_name ? ` · ${a.location.display_name}` : ""}
                  </div>
                  <p className="text-body text-truncate mt-1 mb-0">{a.description}</p>
                  {!!scheduleCounts[a.id] && (
                    <span className="badge bg-success-subtle text-success-emphasis mt-2">
                      {scheduleCounts[a.id]} upcoming schedule{scheduleCounts[a.id] === 1 ? "" : "s"}
                    </span>
                  )}
                  <div className="small text-muted mt-2 border-top pt-2">
                    By {a.creator?.display_name || a.creator?.email || "Unknown"}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {mode === "edit" && selected && (
          <EditActivityModal
            key={selected.id}
            activity={selected}
            onClose={() => {
              setSelected(null);
              setMode(null);
            }}
            onSaved={(updated) => {
              upsertActivity(updated);
              setSelected(null);
              setMode(null);
            }}
            onDeleted={(id) => {
              removeActivity(id);
              setSelected(null);
              setMode(null);
            }}
          />
        )}

        {mode === "view" && selected && (
          <ViewActivityModal
            activity={selected}
            onClose={() => {
              setSelected(null);
              setMode(null);
            }}
          />
        )}
      </main>
    </div>
  );
}
