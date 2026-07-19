// frontend/src/pages/CreateSchedule.jsx
import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { api, ApiError } from "../lib/api";

export default function CreateSchedule() {
  const { token } = useAuth();
  const toast = useToast();
  const [step, setStep] = useState(1);
  const [mode, setMode] = useState(""); // "program" | "activity"

  const [form, setForm] = useState({
    program_id: "",
    activity_id: "",
    start_time: "",
    end_time: "",
    price: "",
  });
  
  const [programs, setPrograms] = useState([]);
  const [activities, setActivities] = useState([]);
  const [programActivities, setProgramActivities] = useState([]);
  const [activitySchedules, setActivitySchedules] = useState({});
  const [error, setError] = useState("");

  const setField = (k, v) => setForm((p) => ({ ...p, [k]: v }));

  // Carga base
  useEffect(() => {
    if (!token) return;
    api.get(`/programs/`).then(setPrograms).catch(() => {});
    api.get(`/activities/`).then(setActivities).catch(() => {});
  }, [token]);

  // Cargar actividades ligadas al programa
  useEffect(() => {
    if (mode === "program" && form.program_id) {
      api
        .get(`/programs/${form.program_id}/activities`)
        .then((data) => {
          setProgramActivities(Array.isArray(data) ? data : []);
          const init = {};
          (Array.isArray(data) ? data : []).forEach((a) => {
            init[a.id] = { start: "", end: "" };
          });
          setActivitySchedules(init);
        })
        .catch(() => setProgramActivities([]));
    }
  }, [mode, form.program_id, token]);

  // Cuando se setean tiempos del programa → asignar por defecto a hijos
  useEffect(() => {
    if (mode === "program" && form.start_time && form.end_time) {
      setActivitySchedules((prev) => {
        const updated = { ...prev };
        Object.keys(updated).forEach((id) => {
          updated[id] = {
            start: form.start_time,
            end: form.end_time,
          };
        });
        return updated;
      });
    }
  }, [form.start_time, form.end_time, mode]);

  const handleActivityScheduleChange = (id, field, value) => {
    setActivitySchedules((prev) => ({
      ...prev,
      [id]: { ...prev[id], [field]: value },
    }));
  };

  const handleSubmit = async () => {
    setError("");
    try {
      if (mode === "activity") {
        // Crear schedule individual
        const payload = {
          activity_id: form.activity_id,
          start_time: form.start_time,
          end_time: form.end_time,
          price: form.price ? parseFloat(form.price) : null,
          min_participants: form.min_participants ? parseInt(form.min_participants) : null,
          max_participants: form.max_participants ? parseInt(form.max_participants) : null,
        };
        try {
          await api.post(`/activity-schedules/`, payload);
        } catch (err) {
          if (err instanceof ApiError && err.status === 401) {
            throw new Error("Tu sesión expiró o no estás autenticado.");
          }
          if (err instanceof ApiError && err.status === 403) {
            throw new Error("No tienes permisos para crear horarios de programas.");
          }
          throw new Error("Error creando el horario del programa");
        }
        toast.success("Activity schedule created!");
      } else if (mode === "program") {
        // Crear program schedule
        const programPayload = {
          program_id: form.program_id,
          start_time: form.start_time,
          end_time: form.end_time,
          price: form.price ? parseFloat(form.price) : null,
        };
        let parent;
        try {
          parent = await api.post(`/program-schedules/`, programPayload);
        } catch {
          throw new Error("Error creating program schedule");
        }

        // Crear hijos (itinerarios)
        for (let [id, times] of Object.entries(activitySchedules)) {
          if (!times.start || !times.end) {
            throw new Error("All activities must have schedules");
          }
          // Validación de ventana
          if (times.start < form.start_time || times.end > form.end_time) {
            throw new Error("Activity schedules must be inside program timeframe");
          }
          const actPayload = {
            program_schedule_id: parent.id,
            activity_id: id,
            start_time: times.start,
            end_time: times.end,
          };
          try {
            await api.post(`/activity-schedules/`, actPayload);
          } catch {
            throw new Error("Error creating activity schedule");
          }
        }

        toast.success("Program and activity schedules created!");
      }
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="container my-4">
      <div className="card shadow-card rounded-xl2">
        <div className="card-body">
          <h2 className="text-h2 mb-4">Create Schedule</h2>
          {error && <p className="text-state-danger">{error}</p>}

          {/* STEP 1 */}
          {step === 1 && (
            <>
              <h3 className="text-h3 mb-3">Choose Schedule Type</h3>
              <div className="d-flex gap-3 mb-3">
                <button
                  type="button"
                  className={`btn ${mode === "program" ? "btn-primary" : "btn-light"}`}
                  onClick={() => setMode("program")}
                >
                  Program Schedule
                </button>
                <button
                  type="button"
                  className={`btn ${mode === "activity" ? "btn-primary" : "btn-light"}`}
                  onClick={() => setMode("activity")}
                >
                  Activity Schedule
                </button>
              </div>

              {mode === "program" && (
                <select
                  className="form-select mb-3"
                  value={form.program_id}
                  onChange={(e) => setField("program_id", e.target.value)}
                >
                  <option value="">-- Select Program --</option>
                  {programs.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title}
                    </option>
                  ))}
                </select>
              )}

              {mode === "activity" && (
                <select
                  className="form-select mb-3"
                  value={form.activity_id}
                  onChange={(e) => setField("activity_id", e.target.value)}
                >
                  <option value="">-- Select Activity --</option>
                  {activities.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.title}
                    </option>
                  ))}
                </select>
              )}

              <button
                className="btn btn-primary"
                disabled={
                  !mode ||
                  (mode === "program" && !form.program_id) ||
                  (mode === "activity" && !form.activity_id)
                }
                onClick={() => setStep(2)}
              >
                Next
              </button>
            </>
          )}

          {/* STEP 2: programa o actividad */}
          {step === 2 && (
            <>
              <h3 className="text-h3 mb-3">Set {mode === "program" ? "Program" : "Activity"} Time</h3>
              <input
                type="datetime-local"
                className="form-control mb-3"
                value={form.start_time}
                onChange={(e) => setField("start_time", e.target.value)}
              />
              <input
                type="datetime-local"
                className="form-control mb-3"
                value={form.end_time}
                onChange={(e) => setField("end_time", e.target.value)}
              />
              <input
                        type="number"
                        className="form-control mb-3"
                        placeholder="Min participants"
                        value={form.min_participants || ""}
                        onChange={(e) => setField("min_participants", e.target.value)}
                      />
                      <input
                        type="number"
                        className="form-control mb-3"
                        placeholder="Max participants"
                        value={form.max_participants || ""}
                        onChange={(e) => setField("max_participants", e.target.value)}
                      />
              <div className="d-flex gap-2">
                <button type="button" className="btn btn-secondary" onClick={() => setStep(1)}>
                  Back
                </button>
                <button type="button" className="btn btn-primary" onClick={() => setStep(3)}>
                  Next
                </button>
              </div>
            </>
          )}

          {/* STEP 3: Program extras */}
          {step === 3 && mode === "program" && (
            <>
              <h3 className="text-h3 mb-3">Set Activity Schedules</h3>
              {(programActivities || []).map((a) => (
                <div key={a.id} className="mb-3">
                  <h4 className="fw-semibold">{a.title}</h4>
                  <input
                    type="datetime-local"
                    className="form-control mb-2"
                    value={activitySchedules[a.id]?.start || ""}
                    onChange={(e) => handleActivityScheduleChange(a.id, "start", e.target.value)}
                  />
                  <input
                    type="datetime-local"
                    className="form-control"
                    value={activitySchedules[a.id]?.end || ""}
                    onChange={(e) => handleActivityScheduleChange(a.id, "end", e.target.value)}
                  />
                </div>
              ))}

              <h3 className="text-h3 mb-3 mt-4">Program Price</h3>
              <input
                type="number"
                className="form-control mb-3"
                placeholder="Optional"
                value={form.price}
                onChange={(e) => setField("price", e.target.value)}
              />

              <div className="d-flex gap-2">
                <button type="button" className="btn btn-secondary" onClick={() => setStep(2)}>
                  Back
                </button>
                <button type="button" className="btn btn-success" onClick={handleSubmit}>
                  Create
                </button>
              </div>
            </>
          )}

          {/* STEP 3: Activity extras */}
          {step === 3 && mode === "activity" && (
            <>
              <h3 className="text-h3 mb-3">Set Price</h3>
              <input
                type="number"
                className="form-control mb-3"
                placeholder="Optional"
                value={form.price}
                onChange={(e) => setField("price", e.target.value)}
              />

              <div className="d-flex gap-2">
                <button type="button" className="btn btn-secondary" onClick={() => setStep(2)}>
                  Back
                </button>
                <button type="button" className="btn btn-success" onClick={handleSubmit}>
                  Create
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
