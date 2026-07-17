// ================================
// src/components/ViewProgramModal.jsx
// ================================
import React, { useEffect, useRef, useState } from "react";
import ViewActivityModal from "../pages/ViewActivityModal";
import { useAuth } from "../context/AuthContext";

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

const normId = (s) => String(s || "").replace(/[\s.\-]/g, "").toUpperCase();

export default function ViewProgramModal({ program, onClose }) {
  const { token, user } = useAuth();

  const [activities, setActivities] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [loadingActs, setLoadingActs] = useState(false);
  const [openActivity, setOpenActivity] = useState(null);

  // --- Booking state ---
  const BLANK = {
    first_name: "",
    last_name: "",
    id_type: "national_id",
    id_number: "",
    birth_date: "",
  };
  const [participants, setParticipants] = useState([{ ...BLANK }]);
  const [selectedProgramSchedule, setSelectedProgramSchedule] = useState(null);
  const prefilledRef = useRef(false);

  // guide-only helpers
  const [thirdParty, setThirdParty] = useState(false);
  const guideIdsRef = useRef({ national_id: "", passport_number: "" });

  const fetchMe = async () => {
    if (!token) return null;
    const r = await fetch(`${API}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!r.ok) return null;
    const me = await r.json();
    guideIdsRef.current = {
      national_id: me?.national_id || "",
      passport_number: me?.passport_number || "",
    };
    return me;
  };

  const prefillFromMe = async () => {
    if (prefilledRef.current || thirdParty) return;
    const me = await fetchMe();
    if (!me) return;
    const idType = me.national_id ? "national_id" : me.passport_number ? "passport" : "national_id";
    const idNum = me.national_id || me.passport_number || "";
    const birth =
      typeof me.birth_date === "string" ? me.birth_date.split("T")[0] : me.birth_date || "";
    setParticipants([
      {
        first_name: me.first_name || "",
        last_name: me.last_name || "",
        id_type: idType,
        id_number: idNum,
        birth_date: birth,
      },
    ]);
    prefilledRef.current = true;
  };

  const handleSelectSchedule = async (s) => {
    setSelectedProgramSchedule(s);
    prefilledRef.current = false; // force prefill on new selection
    await prefillFromMe();
  };

  // ensure guide IDs are known even if thirdParty is enabled
  useEffect(() => {
    if (user?.role === "guide") fetchMe().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // fallback
  useEffect(() => {
    if (!selectedProgramSchedule || prefilledRef.current) return;
    prefillFromMe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProgramSchedule]);

  const isOwner =
    !!user?.id &&
    (program?.creator_id === user?.id ||
      program?.creator?.id === user?.id ||
      program?.creator?.email === user?.email);
  const canBook = !isOwner;

  // Load program activities
  useEffect(() => {
    if (!program?.id) return;
    setLoadingActs(true);
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    fetch(`${API}/programs/${program.id}/activities`, { headers })
      .then((r) => (r.ok ? r.json() : Promise.resolve([])))
      .then((rows) => setActivities(Array.isArray(rows) ? rows : []))
      .catch(() => setActivities([]))
      .finally(() => setLoadingActs(false));
  }, [program?.id, token]);

  // Load program schedules
  useEffect(() => {
    if (!program?.id) return;
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    fetch(`${API}/program-schedules/?program_id=${program.id}`, { headers })
      .then((r) => (r.ok ? r.json() : Promise.resolve([])))
      .then((rows) => setSchedules(Array.isArray(rows) ? rows : []))
      .catch(() => setSchedules([]));
  }, [program?.id, token]);

  // Gallery
  const gallery = normalizeGallery(program?.gallery);
  const [centerIdx, setCenterIdx] = useState(0);
  useEffect(() => {
    const idx0 = gallery.findIndex((x) => x.position === 0);
    setCenterIdx(idx0 >= 0 ? idx0 : 0);
  }, [program?.id, program?.gallery]);
  const n = gallery.length;
  const leftIdx = n ? (centerIdx - 1 + n) % n : 0;
  const rightIdx = n ? (centerIdx + 1) % n : 0;
  const prev = () => n && setCenterIdx((i) => (i - 1 + n) % n);
  const next = () => n && setCenterIdx((i) => (i + 1) % n);

  const addPassenger = () => setParticipants((p) => [...p, { ...BLANK }]);
  const removePassenger = (i) => setParticipants((p) => p.filter((_, idx) => idx !== i));
  const setP = (i, k, v) =>
    setParticipants((p) => p.map((row, idx) => (idx === i ? { ...row, [k]: v } : row)));

  const resetSelection = () => {
    setSelectedProgramSchedule(null);
    setParticipants([{ ...BLANK }]);
    prefilledRef.current = false;
  };

  return (
    <div className="modal show d-block" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
      <div className="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
        <div className="modal-content shadow-modal rounded-xl2">
          <div className="modal-header">
            <h2 className="text-h2 mb-0">{program?.title || "Program"}</h2>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>

          <div className="modal-body">
            {program?.description && <p className="mb-3">{program.description}</p>}

            {/* Gallery */}
            {n > 0 && (
              <div className="mb-4 d-flex justify-content-center">
                <div className="position-relative" style={{ width: "100%", maxWidth: 920 }}>
                  <div
                    className="d-flex justify-content-center align-items-end gap-3"
                    style={{ userSelect: "none" }}
                  >
                    {n > 1 && (
                      <img
                        src={gallery[leftIdx].url}
                        alt={gallery[leftIdx].tag || "left"}
                        onClick={prev}
                        style={{
                          width: 220,
                          height: 160,
                          objectFit: "cover",
                          borderRadius: 12,
                          opacity: 0.85,
                          cursor: "pointer",
                        }}
                      />
                    )}
                    <div className="position-relative">
                      <img
                        src={gallery[centerIdx].url}
                        alt={gallery[centerIdx].tag || "center"}
                        style={{
                          width: 320,
                          height: 220,
                          objectFit: "cover",
                          borderRadius: 16,
                          boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
                        }}
                      />
                      {gallery[centerIdx].position === 0 && (
                        <span
                          className="badge bg-light text-dark position-absolute"
                          style={{ top: 8, left: 8 }}
                        >
                          Cover
                        </span>
                      )}
                    </div>
                    {n > 1 && (
                      <img
                        src={gallery[rightIdx].url}
                        alt={gallery[rightIdx].tag || "right"}
                        onClick={next}
                        style={{
                          width: 220,
                          height: 160,
                          objectFit: "cover",
                          borderRadius: 12,
                          opacity: 0.85,
                          cursor: "pointer",
                        }}
                      />
                    )}
                  </div>
                  {n > 1 && (
                    <>
                      <button
                        type="button"
                        className="btn btn-light position-absolute top-50 start-0 translate-middle-y"
                        onClick={prev}
                        aria-label="Prev"
                      >
                        ‹
                      </button>
                      <button
                        type="button"
                        className="btn btn-light position-absolute top-50 end-0 translate-middle-y"
                        onClick={next}
                        aria-label="Next"
                      >
                        ›
                      </button>
                    </>
                  )}
                </div>
              </div>
            )}

            <h4 className="mt-2 mb-2">Activities in this program</h4>
            <div className="border rounded p-2 mb-3" style={{ maxHeight: 260, overflowY: "auto" }}>
              {loadingActs ? (
                <p className="mb-0">Loading…</p>
              ) : activities.length === 0 ? (
                <p className="mb-0">No activities linked</p>
              ) : (
                <div className="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-3">
                  {activities.map((a) => (
                    <div key={a.id} className="col">
                      <div className="card h-100 border-200">
                        <div className="card-body d-flex justify-content-between align-items-start">
                          <div className="pe-3 text-truncate">
                            <div className="fw-semibold text-truncate">{a.title}</div>
                            <div className="small text-muted text-truncate">
                              {a.activity_type || "–"}
                              {a.location?.display_name ? ` · ${a.location.display_name}` : ""}
                            </div>
                          </div>
                          <button
                            className="btn btn-outline-primary btn-sm"
                            onClick={() => setOpenActivity(a)}
                            type="button"
                          >
                            Ver
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <h4 className="mt-2 mb-2">Available Schedules</h4>
            {schedules.length === 0 ? (
              <p className="mb-0">No schedules available</p>
            ) : (
              <ul className="list-group">
                {schedules.map((s) => (
                  <li
                    key={s.id}
                    className="list-group-item d-flex justify-content-between align-items-center"
                  >
                    <div className="flex-grow-1 me-3">
                      <div className="form-control bg-body-tertiary" style={{ cursor: "default" }}>
                        {new Date(s.start_time).toLocaleString()} –{" "}
                        {new Date(s.end_time).toLocaleString()}
                        {s.price ? ` | $${s.price}` : ""}
                      </div>
                    </div>
                    {canBook && (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => handleSelectSchedule(s)}
                        type="button"
                      >
                        Select
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {canBook && selectedProgramSchedule && (
              <div className="card mt-3 p-3">
                <h5 className="mb-2">Passenger data</h5>

                {user?.role === "guide" && (
                  <div className="form-check form-switch mb-2">
                    <input
                      id="tp-program"
                      className="form-check-input"
                      type="checkbox"
                      checked={thirdParty}
                      onChange={(e) => {
                        const v = e.target.checked;
                        setThirdParty(v);
                        prefilledRef.current = true; // stop future auto-prefill
                        setParticipants([{ ...BLANK }]);
                      }}
                    />
                    <label className="form-check-label" htmlFor="tp-program">
                      Book for others (guide)
                    </label>
                  </div>
                )}

                <div className="text-muted small mb-2">
                  Schedule: {new Date(selectedProgramSchedule.start_time).toLocaleString()} –{" "}
                  {new Date(selectedProgramSchedule.end_time).toLocaleString()}
                </div>

                {/* Header */}
                <div className="row g-2 mb-1">
                  <div className="col-md-3">
                    <label className="form-label small fw-semibold mb-0">First Name</label>
                  </div>
                  <div className="col-md-3">
                    <label className="form-label small fw-semibold mb-0">Last Name</label>
                  </div>
                  <div className="col-md-2">
                    <label className="form-label small fw-semibold mb-0">ID Type</label>
                  </div>
                  <div className="col-md-2">
                    <label className="form-label small fw-semibold mb-0">ID Number</label>
                  </div>
                  <div className="col-md-2">
                    <label className="form-label small fw-semibold mb-0">Birth Date</label>
                  </div>
                </div>

                {participants.map((p, i) => (
                  <div key={i} className="row g-2 align-items-end mb-2">
                    <div className="col-md-3">
                      <input
                        className="form-control"
                        placeholder="First name"
                        value={p.first_name}
                        onChange={(e) => setP(i, "first_name", e.target.value)}
                      />
                    </div>
                    <div className="col-md-3">
                      <input
                        className="form-control"
                        placeholder="Last name"
                        value={p.last_name}
                        onChange={(e) => setP(i, "last_name", e.target.value)}
                      />
                    </div>
                    <div className="col-md-2">
                      <select
                        className="form-select"
                        value={p.id_type}
                        onChange={(e) => setP(i, "id_type", e.target.value)}
                      >
                        <option value="national_id">National ID</option>
                        <option value="passport">Passport</option>
                      </select>
                    </div>
                    <div className="col-md-2">
                      <input
                        className="form-control"
                        placeholder="ID number"
                        value={p.id_number}
                        onChange={(e) => setP(i, "id_number", e.target.value)}
                      />
                    </div>
                    <div className="col-md-2">
                      <input
                        type="date"
                        className="form-control"
                        value={p.birth_date}
                        onChange={(e) => setP(i, "birth_date", e.target.value)}
                      />
                    </div>
                    {participants.length > 1 && (
                      <div className="col-12">
                        <button
                          className="btn btn-sm btn-outline-danger"
                          type="button"
                          onClick={() => removePassenger(i)}
                        >
                          Remove
                        </button>
                      </div>
                    )}
                  </div>
                ))}

                <div className="d-flex gap-2">
                  <button className="btn btn-light" type="button" onClick={addPassenger}>
                    + Add passenger
                  </button>
                  <button
                    className="btn btn-success"
                    type="button"
                    onClick={async () => {
                      if (!token) return alert("Login first");

                      // Guide-only: block passenger with same ID as guide
                      if (user?.role === "guide") {
                        const gids = [
                          guideIdsRef.current.national_id,
                          guideIdsRef.current.passport_number,
                        ]
                          .filter(Boolean)
                          .map(normId);
                        const clash = participants.find((pp) =>
                          gids.includes(normId(pp.id_number))
                        );
                        if (clash) {
                          alert("Invalid: a passenger uses the guide’s ID number.");
                          return;
                        }
                      }

                      try {
                        const res = await fetch(`${API}/bookings/`, {
                          method: "POST",
                          headers: {
                            "Content-Type": "application/json",
                            Authorization: `Bearer ${token}`,
                          },
                          body: JSON.stringify({
                            program_schedule_id: selectedProgramSchedule.id,
                            participants,
                          }),
                        });
                        const j = await res.json().catch(() => ({}));
                        if (res.status === 401) {
                          alert("Sesión expirada. Inicia sesión nuevamente.");
                          return;
                        }
                        if (!res.ok) {
                          alert(j?.detail || "Error");
                          return;
                        }
                        alert("Booking created");
                        resetSelection();
                      } catch {
                        alert("Network error");
                      }
                    }}
                  >
                    Book now
                  </button>
                  <button className="btn btn-outline-secondary" type="button" onClick={resetSelection}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button onClick={onClose} className="btn btn-secondary">
              Close
            </button>
          </div>
        </div>
      </div>

      {openActivity && (
        <ViewActivityModal
          activity={openActivity}
          onClose={() => setOpenActivity(null)}
          hideBookings
        />
      )}
    </div>
  );
}
