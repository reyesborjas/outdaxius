import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { api } from "../lib/api";

/* --- Modal para subir voucher --- */
function PayModal({ booking, onClose, onDone }) {
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [voucherUrl, setVoucherUrl] = useState("");
  const [reference, setReference] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    setErr("");
    if (!amount) {
      setErr("Amount required");
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/bookings/${booking.id}/pay`, {
        amount: Number(amount),
        currency,
        voucher_url: voucherUrl || null,
        reference: reference || null,
      });
      onDone();
      onClose();
    } catch (e) {
      setErr(String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="modal d-block"
      tabIndex="-1"
      role="dialog"
      style={{ background: "rgba(0,0,0,.3)" }}
    >
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Payment voucher</h5>
            <button className="btn-close" onClick={onClose} />
          </div>
          <div className="modal-body">
            <div className="mb-2">
              <label className="form-label">Amount</label>
              <input
                className="form-control"
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </div>
            <div className="mb-2">
              <label className="form-label">Currency</label>
              <input
                className="form-control"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
              />
            </div>
            <div className="mb-2">
              <label className="form-label">Voucher image URL</label>
              <input
                className="form-control"
                placeholder="https://..."
                value={voucherUrl}
                onChange={(e) => setVoucherUrl(e.target.value)}
              />
            </div>
            <div className="mb-2">
              <label className="form-label">Reference</label>
              <input
                className="form-control"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
              />
            </div>
            {err && <div className="text-danger small">{err}</div>}
          </div>
          <div className="modal-footer">
            <button className="btn btn-light" onClick={onClose} disabled={submitting}>
              Close
            </button>
            <button className="btn btn-primary" onClick={submit} disabled={submitting}>
              Submit
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const REFUND_BADGE = {
  manual: "bg-warning",
  succeeded: "bg-success",
  failed: "bg-danger",
  not_required: "bg-secondary",
};

/* --- Modal de confirmación de cancelación --- */
function CancelModal({ booking, onClose, onDone }) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");
  const toast = useToast();

  const submit = async () => {
    setSubmitting(true);
    setErr("");
    try {
      const data = await api.post(`/bookings/${booking.id}/cancel`, { reason: reason.trim() || null });
      const fee = Number(data.cancellation_fee || 0);
      toast.success(
        fee > 0
          ? `Cancelled. Fee: $${data.cancellation_fee} — refund: $${data.refund_amount}${
              data.refund_status === "manual" ? " (to be returned by the vendor)" : ""
            }`
          : "Cancelled with no fee — full refund."
      );
      onDone();
      onClose();
    } catch (e) {
      setErr(e.message || "Could not cancel this booking");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal d-block" tabIndex="-1" role="dialog" style={{ background: "rgba(0,0,0,.3)" }}>
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Cancel booking</h5>
            <button className="btn-close" onClick={onClose} disabled={submitting} />
          </div>
          <div className="modal-body">
            <p className="text-muted small mb-3">
              Cancellation fees depend on how close to the start date you cancel (full refund 7+
              days out, 70% fee 1-7 days out, 100% fee under 24 hours). You'll see the exact fee
              and refund amount once you confirm.
            </p>
            <label className="form-label small">Reason (optional)</label>
            <input
              className="form-control"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Let us know why you're cancelling"
            />
            {err && <div className="text-danger small mt-2">{err}</div>}
          </div>
          <div className="modal-footer">
            <button className="btn btn-light" onClick={onClose} disabled={submitting}>
              Keep booking
            </button>
            <button className="btn btn-danger" onClick={submit} disabled={submitting}>
              {submitting ? "Cancelling…" : "Confirm cancellation"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* --- Página principal --- */
export default function Bookings() {
  const { token, loading } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [programSchedules, setProgramSchedules] = useState([]);
  const [activitySchedules, setActivitySchedules] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [activities, setActivities] = useState([]);
  const [error, setError] = useState("");
  const [paying, setPaying] = useState(null);
  const [cancelling, setCancelling] = useState(null);
  const [editingParticipant, setEditingParticipant] = useState(null);
  const [participant, setParticipant] = useState(null);

  const fetchData = async () => {
    try {
      const [bookingsData, progSchedData, actSchedData, progData, actData] = await Promise.all([
        api.get(`/bookings/`).catch(() => []),
        api.get(`/program-schedules/`).catch(() => []),
        api.get(`/activity-schedules/`).catch(() => []),
        api.get(`/programs/`).catch(() => []),
        api.get(`/activities/`).catch(() => []),
      ]);

      setBookings(bookingsData);
      setProgramSchedules(progSchedData);
      setActivitySchedules(actSchedData);
      setPrograms(progData);
      setActivities(actData);
    } catch (err) {
      console.error(err);
      setError("Error fetching bookings");
    }
  };

  const resolveTitle = (booking) => {
    if (booking.activity_schedule_id) {
      const sched = activitySchedules.find((s) => s.id === booking.activity_schedule_id);
      if (sched) {
        const activity = activities.find((a) => a.id === sched.activity_id);
        return activity?.title || "(activity)";
      }
    }
    if (booking.program_schedule_id) {
      const sched = programSchedules.find((s) => s.id === booking.program_schedule_id);
      if (sched) {
        const program = programs.find((p) => p.id === sched.program_id);
        return program?.title || "(program)";
      }
    }
    return "(unknown)";
  };

  useEffect(() => {
    if (token) fetchData();
  }, [token]);

  if (loading) return null;

  return (
    <div className="min-vh-100 d-flex flex-column bg-surface-light">
      <main className="flex-grow-1 container-lg px-3 py-4">
        <div className="d-flex justify-content-between align-items-center mb-4">
          <h2 className="text-h1">My Bookings</h2>
        </div>

        {error && <p className="text-state-danger">{error}</p>}

        <div className="table-responsive">
          <table className="table table-striped align-middle">
            <thead>
              <tr>
                <th>Schedule</th>
                <th>Status</th>
                <th>Attendance</th>
                <th>Updated</th>
                <th>Cancelled</th>
                <th>Fee</th>
                <th>Refund</th>
                <th className="d-flex gap-2 text-nowrap">Actions</th>
              </tr>
            </thead>
            <tbody>
              {bookings.map((b) => {
                return (
                  <tr key={b.id}>
                    <td>{resolveTitle(b)}</td>
                    <td>{b.status}</td>
                    <td>{b.attendance_status || "-"}</td>
                    <td>{b.updated_at ? new Date(b.updated_at).toLocaleString() : "-"}</td>
                    <td>{b.cancelled_at ? new Date(b.cancelled_at).toLocaleString() : "-"}</td>
                    <td>{b.cancellation_fee != null ? `$${b.cancellation_fee}` : "-"}</td>
                    <td>
                      {b.refund_status ? (
                        <>
                          {b.refund_amount != null && `$${b.refund_amount} `}
                          <span className={`badge ${REFUND_BADGE[b.refund_status] || "bg-secondary"}`}>
                            {b.refund_status}
                          </span>
                        </>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td className="d-flex gap-2">
                      {b.status !== "cancelled" ? (
                        <>
                        <button onClick={() => setEditingParticipant(participant)}>Editar</button>

                                    {editingParticipant &&
                                      <ParticipantEditModal
                                        participant={editingParticipant}
                                        onClose={() => setEditingParticipant(null)}
                                        onSave={async (updated) => {
                                          await api.patch(`/bookings/${booking.id}/participants/${updated.id}`, updated);
                                          setEditingParticipant(null);
                                          fetchData(); // refresca lista
                                        }}
                                      />
                                    }

                          <button className="btn btn-sm btn-outline-primary" onClick={() => setPaying(b)}>
                            Pay
                          </button>
                          <button
                            className="btn btn-sm btn-outline-danger"
                            onClick={() => setCancelling(b)}
                          >
                            Cancel
                          </button>

                        </>
                      ) : (
                        <span className="text-muted">Cancelled</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {paying && (
          <PayModal booking={paying} onClose={() => setPaying(null)} onDone={fetchData} />
        )}
        {cancelling && (
          <CancelModal booking={cancelling} onClose={() => setCancelling(null)} onDone={fetchData} />
        )}
      </main>
    </div>
  );
}
