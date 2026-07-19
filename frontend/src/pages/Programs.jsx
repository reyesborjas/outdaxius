// frontend/src/pages/Programs.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useLocation, useNavigate } from "react-router-dom";
import EditProgramModal from "./EditProgramModal";
import ViewProgramModal from "./ViewProgramModal";
import SearchBar from "../components/SearchBar";
import { api } from "../lib/api";

// normaliza y ordena galería por position
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

// obtiene cover (position === 0) o primera
function coverOf(gallery) {
  const arr = normalizeGallery(gallery);
  if (!arr.length) return null;
  return arr.find((x) => x.position === 0) || arr[0];
}

export default function Programs() {
  const { user, loading } = useAuth();
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
  const [searching, setSearching] = useState(false);

  const [selected, setSelected] = useState(null);
  const [mode, setMode] = useState(null); // "edit" | "view"

  useEffect(() => {
    let alive = true;
    api
      .get(`/programs/`, { skipAuth: true })
      .then((data) => {
        if (!alive) return;
        const normal = (Array.isArray(data) ? data : []).map((p) => ({
          ...p,
          gallery: normalizeGallery(p.gallery),
        }));
        setAll(normal);
        setList([...normal].sort((a, b) => a.title.localeCompare(b.title)));
      })
      .catch(() => {
        if (!alive) return;
        setAll([]);
        setList([]);
      });
    return () => {
      alive = false;
    };
  }, []);

  // Bulk-fetch schedules once so each card can show an "N upcoming" badge without an N+1
  // request-per-card. Public/unscoped on purpose -- this is the customer-facing browse view.
  useEffect(() => {
    let alive = true;
    api
      .get(`/program-schedules/`, { skipAuth: true })
      .then((rows) => {
        if (!alive) return;
        const now = Date.now();
        const counts = {};
        (Array.isArray(rows) ? rows : []).forEach((s) => {
          if (!s.program_id) return;
          if (s.start_time && new Date(s.start_time).getTime() < now) return;
          counts[s.program_id] = (counts[s.program_id] || 0) + 1;
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
  }, []);

  const canEdit = (p) => {
    if (!inDashboard || !user) return false;
    if (user.role === "admin") return true;
    const isOwner =
      (p?.creator?.id && p.creator.id === user.id) ||
      (p?.creator_id && p.creator_id === user.id) ||
      (p?.created_by && p.created_by === user.id) ||
      (p?.creator?.email && p.creator.email === user.email);
    return user.role === "guide" && isOwner;
  };

  const upsertProgram = (item) =>
    setList((xs) => {
      const cleaned = { ...item, gallery: normalizeGallery(item.gallery) };
      const has = xs.some((a) => a.id === item.id);
      const arr = has ? xs.map((a) => (a.id === item.id ? cleaned : a)) : [...xs, cleaned];
      return [...arr].sort((a, b) => a.title.localeCompare(b.title));
    });
  const removeProgram = (id) => setList((xs) => xs.filter((a) => a.id !== id));

  const clearSearch = () => {
    setQ("");
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
      // Optionally, do server-side search (add a /programs/search endpoint).
      // For now, simple local filter.
      const filtered = all.filter((p) => {
        const t = (p?.title || "").toLowerCase();
        const desc = (p?.description || "").toLowerCase();
        return t.includes(text) || desc.includes(text);
      });
      setList(filtered.sort((a, b) => a.title.localeCompare(b.title)));
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
            scope={null} // or add a scope if you want filtering later
            onChange={setQ}
            onScopeChange={() => {}}
            onSearch={runSearch}
            onClear={clearSearch}
            loading={searching}
            placeholder="Search programs… (title or description)"
            className="flex-grow-1"
          />
          {inDashboard && user && (user.role === "admin" || user.role === "guide") && (
            <button
              onClick={() => navigate(`${dashBase}/create-program`)}
              className="btn btn-primary ms-auto"
              type="button"
            >
              + New Program
            </button>
          )}
        </div>

        <div className="row row-cols-1 row-cols-sm-2 row-cols-lg-3 g-3">
          {list.map((p) => {
            const cover = coverOf(p.gallery);
            return (
              <div key={p.id} className="col">
                <div
                  className="position-relative border rounded p-card bg-surface-snow shadow-card h-100 cursor-pointer"
                  onClick={() => {
                    if (!inDashboard) {
                      setSelected(p);
                      setMode("view");
                    }
                  }}
                >
                  {cover && (
                    <img
                      src={cover.url}
                      alt={cover.tag || p.title}
                      className="w-100 rounded mb-2"
                      style={{ height: "160px", objectFit: "cover" }}
                    />
                  )}

                  {inDashboard && canEdit(p) && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelected(p);
                        setMode("edit");
                      }}
                      className="btn btn-light btn-sm position-absolute top-0 start-0 m-2 shadow-card rounded-circle"
                      title="Edit program"
                      type="button"
                    >
                      ✎
                    </button>
                  )}

                  {inDashboard && user && !canEdit(p) && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelected(p);
                        setMode("view");
                      }}
                      className="btn btn-light btn-sm position-absolute top-0 start-50 translate-middle-x m-2 shadow-card rounded-circle"
                      title="View program"
                      type="button"
                    >
                      👁
                    </button>
                  )}

                  <h3 className="fw-bold">{p.title}</h3>
                  <div className="small text-muted">{p.type?.type_name || "–"}</div>
                  <p className="text-body text-truncate">{p.description}</p>
                  {!!scheduleCounts[p.id] && (
                    <span className="badge bg-success-subtle text-success-emphasis mt-2">
                      {scheduleCounts[p.id]} upcoming schedule{scheduleCounts[p.id] === 1 ? "" : "s"}
                    </span>
                  )}
                  <div className="small text-muted mt-2 border-top pt-2">
                    By {p.creator?.display_name || p.creator?.email || "Unknown"}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {mode === "edit" && selected && (
          <EditProgramModal
            key={selected.id}
            program={selected}
            onClose={() => {
              setSelected(null);
              setMode(null);
            }}
            onSaved={(updated) => {
              upsertProgram(updated);
              setSelected(null);
              setMode(null);
            }}
            onDeleted={(id) => {
              removeProgram(id);
              setSelected(null);
              setMode(null);
            }}
          />
        )}

        {mode === "view" && selected && (
          <ViewProgramModal
            program={selected}
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
