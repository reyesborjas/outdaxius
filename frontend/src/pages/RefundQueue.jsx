// frontend/src/pages/RefundQueue.jsx
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";

const API = (import.meta.env.VITE_API || "http://127.0.0.1:8000/api").replace(/\/$/, "");

export default function RefundQueue() {
  const { fetchWithAuth } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [resolvingId, setResolvingId] = useState(null);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetchWithAuth(`${API}/admin/refunds/manual-queue`, {
        headers: { Accept: "application/json" },
      });
      if (!res.ok) throw new Error(`Error ${res.status} loading refund queue`);
      setBookings(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [fetchWithAuth]);

  useEffect(() => { loadQueue(); }, [loadQueue]);

  const resolve = async (bookingId, outcome) => {
    const note = window.prompt(`Note for marking this refund as "${outcome}" (optional):`) || "";
    setResolvingId(bookingId);
    try {
      const res = await fetchWithAuth(`${API}/admin/refunds/${bookingId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ outcome, note }),
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Could not resolve refund");
      }
      await loadQueue();
    } catch (e) {
      setError(e.message);
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div className="container py-4">
      <h2 className="text-h2 mb-3">Manual Refund Queue</h2>
      <p className="text-muted">
        Bookings where the vendor's payment gateway could not process an automatic refund
        (e.g. insufficient balance) land here for manual resolution.
      </p>

      {error && <div className="alert alert-danger">{error}</div>}

      {loading ? (
        <div className="text-center py-4">
          <div className="spinner-border" role="status" />
        </div>
      ) : bookings.length === 0 ? (
        <div className="alert alert-info">No refunds pending manual resolution.</div>
      ) : (
        <div className="table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th>Booking</th>
                <th>Cancelled at</th>
                <th>Refund amount</th>
                <th>Reason</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {bookings.map((b) => (
                <tr key={b.booking_id}>
                  <td><code>{b.booking_id}</code></td>
                  <td>{b.cancelled_at ? new Date(b.cancelled_at).toLocaleString() : "-"}</td>
                  <td>{b.refund_amount ?? "-"}</td>
                  <td>{b.cancellation_reason || "-"}</td>
                  <td className="text-end">
                    <button
                      className="btn btn-sm btn-success me-2"
                      disabled={resolvingId === b.booking_id}
                      onClick={() => resolve(b.booking_id, "succeeded")}
                    >
                      Mark resolved
                    </button>
                    <button
                      className="btn btn-sm btn-outline-danger"
                      disabled={resolvingId === b.booking_id}
                      onClick={() => resolve(b.booking_id, "failed")}
                    >
                      Mark failed
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
