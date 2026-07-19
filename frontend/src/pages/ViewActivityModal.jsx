// frontend/src/pages/ViewActivityModal.jsx
import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { api, ApiError } from "../lib/api";

export default function ViewActivityModal({
  activity: activityProp,
  activityId,
  onClose,
  hideBookings = false,
}) {
  const { token, user } = useAuth();
  const toast = useToast();

  const [activity, setActivity] = useState(activityProp || null);
  const [schedules, setSchedules] = useState([]);
  const [loadingActivity, setLoadingActivity] = useState(false);
  const [loadingSchedules, setLoadingSchedules] = useState(false);
  const [error, setError] = useState("");

  const BLANK = {
    first_name: "",
    last_name: "",
    id_type: "national_id",
    id_number: "",
    birth_date: "",
  };
  const [participants, setParticipants] = useState([{ ...BLANK }]);
  const [selectedSchedule, setSelectedSchedule] = useState(null);
  const [thirdParty, setThirdParty] = useState(false);
  const guideIdsRef = useRef({ national_id: "", passport_number: "" });
  const normId = (s) => String(s || "").replace(/[\s.\-]/g, "").toUpperCase();
  const prefilledRef = useRef(false);

  const fetchMe = async () => {
    if (!token) return null;
    let me;
    try {
      me = await api.get(`/users/me`);
    } catch {
      return null;
    }
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
    const idType = me.national_id
      ? "national_id"
      : me.passport_number
      ? "passport"
      : "national_id";
    const idNum = me.national_id || me.passport_number || "";
    const birth =
      typeof me.birth_date === "string"
        ? me.birth_date.split("T")[0]
        : me.birth_date || "";
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
    setSelectedSchedule(s);
    prefilledRef.current = false;
    await prefillFromMe();
  };

  useEffect(() => {
    if (!selectedSchedule || prefilledRef.current) return;
    prefillFromMe();
  }, [selectedSchedule]);

  useEffect(() => {
    if (activity || !activityId) return;
    setLoadingActivity(true);
    api
      .get(`/activities/${activityId}`, { skipAuth: !token })
      .then((a) => setActivity(a || null))
      .catch(() => setError("No se pudo cargar la actividad"))
      .finally(() => setLoadingActivity(false));
  }, [activity, activityId, token]);

  useEffect(() => {
    if (hideBookings || !activity?.id) return;
    setLoadingSchedules(true);
    api
      .get(`/activity-schedules/?activity_id=${activity.id}`, { skipAuth: !token })
      .then((rows) => {
        const arr = Array.isArray(rows) ? rows : [];
        const clean = arr
          .filter((s) => !s.program_schedule_id && !s.program_id)
          .filter((s, i, a) => a.findIndex((x) => x.id === s.id) === i);
        setSchedules(clean);
      })
      .catch(() => setSchedules([]))
      .finally(() => setLoadingSchedules(false));
  }, [activity?.id, token, hideBookings]);

  const gallery = Array.isArray(activity?.gallery) ? activity.gallery : [];
  const normalized = gallery
    .map((g, i) =>
      typeof g === "string"
        ? { url: g, tag: "", position: i }
        : {
            url: g?.url,
            tag: g?.tag || "",
            position:
              Number.isFinite(Number(g?.position)) ? Number(g.position) : i,
          }
    )
    .filter((x) => !!x.url)
    .sort((a, b) => a.position - b.position);

  const [centerIdx, setCenterIdx] = useState(0);
  useEffect(() => {
    const idx0 = normalized.findIndex((x) => x.position === 0);
    setCenterIdx(idx0 >= 0 ? idx0 : 0);
  }, [activity?.id, activity?.gallery]);

  const n = normalized.length;
  const leftIdx = n ? (centerIdx - 1 + n) % n : 0;
  const rightIdx = n ? (centerIdx + 1) % n : 0;
  const prev = () => n && setCenterIdx((i) => (i - 1 + n) % n);
  const next = () => n && setCenterIdx((i) => (i + 1) % n);

  const addPassenger = () =>
    setParticipants((p) => [...p, { ...BLANK }]);
  const removePassenger = (i) =>
    setParticipants((p) => p.filter((_, idx) => idx !== i));
  const setP = (i, k, v) =>
    setParticipants((p) => p.map((row, idx) => (idx === i ? { ...row, [k]: v } : row)));

  const isOwner =
    !!user?.id &&
    (activity?.creator_id === user?.id ||
      activity?.creator?.id === user?.id ||
      activity?.creator?.email === user?.email);
  const canBook = !hideBookings && !isOwner;

  const resetSelection = () => {
    setSelectedSchedule(null);
    setParticipants([{ ...BLANK }]);
    prefilledRef.current = false;
  };

  return (
    <div
      className="modal show d-block"
      style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
    >
      <div className="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
        <div className="modal-content shadow-modal rounded-xl2">
          <div className="modal-header">
            <h2 className="text-h2 mb-0">
              {loadingActivity ? "Loading…" : activity?.title || "Activity"}
            </h2>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>

          <div className="modal-body">
            {error && <p className="text-state-danger">{error}</p>}
            {activity?.description && <p className="mb-2">{activity.description}</p>}

            {/* 🔥 RESPONSIVE: Info Grid */}
            <div className="row g-2 mb-3">
              <div className="col-12 col-sm-6">
                <strong>Type:</strong> {activity?.type?.type_name || "—"}
              </div>
              {activity?.location?.display_name && (
                <div className="col-12 col-sm-6">
                  <strong>Location:</strong> {activity.location.display_name}
                </div>
              )}
            </div>

            {/* 🔥 RESPONSIVE: Gallery */}
            {n > 0 && (
              <div className="mb-3">
                <div className="position-relative" style={{ width: "100%" }}>
                  <div className="d-flex flex-column flex-md-row justify-content-center align-items-center gap-2 gap-md-3" style={{ userSelect: "none" }}>
                    {n > 1 && (
                      <img
                        src={normalized[leftIdx].url}
                        alt={normalized[leftIdx].tag || "left"}
                        onClick={prev}
                        className="d-none d-md-block"
                        style={{ width: 180, height: 120, objectFit: "cover", borderRadius: 12, opacity: 0.85, cursor: "pointer" }}
                      />
                    )}
                    <div className="position-relative w-100" style={{ maxWidth: 480 }}>
                      <img
                        src={normalized[centerIdx].url}
                        alt={normalized[centerIdx].tag || "center"}
                        className="w-100"
                        style={{ height: 220, objectFit: "cover", borderRadius: 16, boxShadow: "0 8px 24px rgba(0,0,0,0.25)" }}
                      />
                      {normalized[centerIdx].position === 0 && (
                        <span className="badge bg-light text-dark position-absolute" style={{ top: 8, left: 8 }}>
                          Cover
                        </span>
                      )}
                    </div>
                    {n > 1 && (
                      <img
                        src={normalized[rightIdx].url}
                        alt={normalized[rightIdx].tag || "right"}
                        onClick={next}
                        className="d-none d-md-block"
                        style={{ width: 180, height: 120, objectFit: "cover", borderRadius: 12, opacity: 0.85, cursor: "pointer" }}
                      />
                    )}
                  </div>
                  {n > 1 && (
                    <>
                      <button type="button" className="btn btn-light position-absolute top-50 start-0 translate-middle-y" onClick={prev} aria-label="Prev">
                        ‹
                      </button>
                      <button type="button" className="btn btn-light position-absolute top-50 end-0 translate-middle-y" onClick={next} aria-label="Next">
                        ›
                      </button>
                    </>
                  )}
                </div>
              </div>
            )}

            {!hideBookings && (
              <>
                <h4 className="mt-3">Available Schedules</h4>
                {loadingSchedules ? (
                  <p>Loading…</p>
                ) : schedules.length === 0 ? (
                  <p>No schedules available</p>
                ) : (
                  <ul className="list-group">
                    {schedules.map((s) => (
                      <li
                        key={s.id}
                        className="list-group-item d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center gap-2"
                      >
                        <span className="flex-grow-1">
                          {new Date(s.start_time).toLocaleString()} – {new Date(s.end_time).toLocaleString()}
                          {s.price ? ` | $${s.price}` : ""}
                        </span>
                        {canBook && (
                          <button
                            className="btn btn-sm btn-primary"
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

                {canBook && selectedSchedule && (
                  <div className="card mt-3 p-3">
                    <h5 className="mb-2">Passenger data</h5>
                    {user?.role === "guide" && (
                      <div className="form-check form-switch mb-2">
                        <input
                          id="tp-activity"
                          className="form-check-input"
                          type="checkbox"
                          checked={thirdParty}
                          onChange={(e) => {
                            const v = e.target.checked;
                            setThirdParty(v);
                            prefilledRef.current = true;
                            setParticipants([{ ...BLANK }]);
                          }}
                        />
                        <label className="form-check-label" htmlFor="tp-activity">
                          Book for others (guide)
                        </label>
                      </div>
                    )}
                    <div className="text-muted small mb-2">
                      Schedule: {new Date(selectedSchedule.start_time).toLocaleString()} – {new Date(selectedSchedule.end_time).toLocaleString()}
                    </div>

                    {/* 🔥 RESPONSIVE: Participant Form Headers (hidden on mobile) */}
                    <div className="row g-2 mb-1 d-none d-md-flex">
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
                      <div key={i} className="border rounded p-2 mb-2">
                        <div className="row g-2 align-items-end">
                          <div className="col-12 col-md-3">
                            <label className="form-label small d-md-none">First Name</label>
                            <input
                              className="form-control form-control-sm"
                              placeholder="First name"
                              value={p.first_name}
                              onChange={(e) => setP(i, "first_name", e.target.value)}
                            />
                          </div>
                          <div className="col-12 col-md-3">
                            <label className="form-label small d-md-none">Last Name</label>
                            <input
                              className="form-control form-control-sm"
                              placeholder="Last name"
                              value={p.last_name}
                              onChange={(e) => setP(i, "last_name", e.target.value)}
                            />
                          </div>
                          <div className="col-12 col-md-2">
                            <label className="form-label small d-md-none">ID Type</label>
                            <select
                              className="form-select form-select-sm"
                              value={p.id_type}
                              onChange={(e) => setP(i, "id_type", e.target.value)}
                            >
                              <option value="national_id">National ID</option>
                              <option value="passport">Passport</option>
                            </select>
                          </div>
                          <div className="col-12 col-md-2">
                            <label className="form-label small d-md-none">ID Number</label>
                            <input
                              className="form-control form-control-sm"
                              placeholder="ID number"
                              value={p.id_number}
                              onChange={(e) => setP(i, "id_number", e.target.value)}
                            />
                          </div>
                          <div className="col-12 col-md-2">
                            <label className="form-label small d-md-none">Birth Date</label>
                            <input
                              type="date"
                              className="form-control form-control-sm"
                              value={p.birth_date}
                              onChange={(e) => setP(i, "birth_date", e.target.value)}
                            />
                          </div>
                        </div>
                        {participants.length > 1 && (
                          <button
                            className="btn btn-sm btn-outline-danger mt-2"
                            type="button"
                            onClick={() => removePassenger(i)}
                          >
                            Remove
                          </button>
                        )}
                      </div>
                    ))}

                    <div className="d-flex flex-column flex-sm-row gap-2 mt-3">
                      <button
                        className="btn btn-light"
                        type="button"
                        onClick={addPassenger}
                      >
                        + Add passenger
                      </button>
                      <button
                        className="btn btn-success"
                        type="button"
                        onClick={async () => {
                          if (!token) return toast.error("Login first");
                          const gids = [
                            guideIdsRef.current.national_id,
                            guideIdsRef.current.passport_number,
                          ].filter(Boolean).map(normId);
                          const clash = participants.find(
                            (pp) => gids.includes(normId(pp.id_number))
                          );
                          if (clash) {
                            toast.error("Invalid: a passenger uses the guide's ID number.");
                            return;
                          }
                          try {
                            await api.post(`/bookings/`, {
                              activity_schedule_id: selectedSchedule.id,
                              participants,
                            });
                            toast.success("Booking created");
                            resetSelection();
                          } catch (err) {
                            if (err instanceof ApiError && err.status === 401) {
                              toast.error("Sesión expirada. Inicia sesión nuevamente.");
                            } else if (err instanceof ApiError) {
                              toast.error(err.message || "Error");
                            } else {
                              toast.error("Network error");
                            }
                          }
                        }}
                      >
                        Book now
                      </button>
                      <button
                        className="btn btn-outline-secondary"
                        type="button"
                        onClick={resetSelection}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          <div className="modal-footer d-flex justify-content-between align-items-center">
            <span className="small text-muted">
              By {activity?.creator?.display_name || activity?.creator?.email || "Unknown"}
            </span>
            <button onClick={onClose} className="btn btn-secondary">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}