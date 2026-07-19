import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";

const API = import.meta.env.VITE_API || "http://127.0.0.1:8000/api";

export default function Schedules() {
  const { token, loading } = useAuth();
  const [programSchedules, setProgramSchedules] = useState([]);
  const [activitySchedules, setActivitySchedules] = useState([]);
  const [error, setError] = useState("");

  const deduplicateById = (arr) => {
    const seen = new Set();
    return arr.filter((item) => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    });
  };

  const fetchSchedules = async () => {
    try {
      const [progSchedRes, actSchedRes, progRes, actRes] = await Promise.all([
        fetch(`${API}/program-schedules/?mine_only=true`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API}/activity-schedules/?mine_only=true`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API}/programs/`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API}/activities/`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      const progSchedulesData = progSchedRes.ok ? await progSchedRes.json() : [];
      const actSchedulesData = actSchedRes.ok ? await actSchedRes.json() : [];
      const allPrograms = progRes.ok ? await progRes.json() : [];
      const allActivities = actRes.ok ? await actRes.json() : [];

      // Normalize Program Schedules
      const progNormalized = progSchedulesData.map((p) => {
        const program = allPrograms.find((pr) => pr.id === p.program_id);
        return {
          id: p.id,
          title: program?.title ?? "(no title)",
          start_time: p.start_time,
          end_time: p.end_time,
          max_participants: program?.max_participants ?? "-",
          bookings_count: p.bookings_count ?? 0,
          price: p.price ?? "-",
          updated_at: p.updated_at,
          status: p.status ?? "pending",
        };
      });

      // Normalize Activity Schedules (exclude those linked to a program)
      const actNormalized = actSchedulesData
        .filter((a) => !a.program_schedule_id) // FIX: remove program-linked activities
        .map((a) => {
          const activity = allActivities.find((ac) => ac.id === a.activity_id);

          return {
            id: a.id,
            relatedProgram: "-",
            title: activity?.title ?? "(no title)",
            start_time: a.start_time,
            end_time: a.end_time,
            max_participants: activity?.max_participants ?? "-",
            bookings_count: a.bookings_count ?? 0,
            price: a.price ?? "-",
            updated_at: a.updated_at,
            status: a.status ?? "pending",
          };
        });

      setProgramSchedules(deduplicateById(progNormalized));
      setActivitySchedules(deduplicateById(actNormalized));
    } catch (err) {
      console.error(err);
      setError("Error fetching schedules");
    }
  };

  useEffect(() => {
    if (token) fetchSchedules();
  }, [token]);

  if (loading) return null;

  return (
    <div className="min-vh-100 d-flex flex-column bg-surface-light">
      <main className="flex-grow-1 container-lg px-3 py-4">
        <div className="d-flex justify-content-between align-items-center mb-1">
          <h2 className="text-h1">Schedules</h2>
        </div>
        <p className="text-muted mb-4">Showing schedules created by your team or company.</p>

        {error && <p className="text-state-danger">{error}</p>}

        {/* Program Schedules */}
        <h3 className="mt-4">Program Schedules</h3>
        <div className="table-responsive mb-5">
          <table className="table table-striped align-middle">
            <thead>
              <tr>
                <th>Title</th>
                <th>Start</th>
                <th>End</th>
                <th>Max Participants</th>
                <th>Bookings</th>
                <th>Price</th>
                <th>Updated</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {programSchedules.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center">No program schedules found</td>
                </tr>
              ) : (
                programSchedules.map((p) => (
                  <tr key={p.id}>
                    <td>{p.title}</td>
                    <td>{new Date(p.start_time).toLocaleString()}</td>
                    <td>{new Date(p.end_time).toLocaleString()}</td>
                    <td>{p.max_participants}</td>
                    <td>{p.bookings_count}</td>
                    <td>{p.price ? `$${p.price}` : "-"}</td>
                    <td>{p.updated_at ? new Date(p.updated_at).toLocaleString() : "-"}</td>
                    <td>{p.status}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Activity Schedules */}
        <h3 className="mt-4">Activity Schedules</h3>
        <div className="table-responsive">
          <table className="table table-striped align-middle">
            <thead>
              <tr>
                <th>Related Program</th>
                <th>Title</th>
                <th>Start</th>
                <th>End</th>
                <th>Max Participants</th>
                <th>Bookings</th>
                <th>Price</th>
                <th>Updated</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {activitySchedules.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center">No activity schedules found</td>
                </tr>
              ) : (
                activitySchedules.map((a) => (
                  <tr key={a.id}>
                    <td>{a.relatedProgram}</td>
                    <td>{a.title}</td>
                    <td>{new Date(a.start_time).toLocaleString()}</td>
                    <td>{new Date(a.end_time).toLocaleString()}</td>
                    <td>{a.max_participants}</td>
                    <td>{a.bookings_count}</td>
                    <td>{a.price ? `$${a.price}` : "-"}</td>
                    <td>{a.updated_at ? new Date(a.updated_at).toLocaleString() : "-"}</td>
                    <td>{a.status}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
