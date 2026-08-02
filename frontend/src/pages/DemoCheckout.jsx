// frontend/src/pages/DemoCheckout.jsx
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { api } from "../lib/api";

export default function DemoCheckout() {
  const { providerRef } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const toast = useToast();

  const [payment, setPayment] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api
      .get(`/payments/demo/${providerRef}`)
      .then((d) => alive && setPayment(d))
      .catch((e) => alive && setError(e.message || "Payment not found"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [providerRef]);

  const resolve = async (outcome) => {
    setSubmitting(true);
    try {
      const result = await api.post(`/payments/demo/${providerRef}/complete`, { outcome });
      toast[outcome === "succeeded" ? "success" : "error"](
        outcome === "succeeded" ? "Payment successful — booking confirmed" : "Payment declined"
      );
      if (user?.email) navigate(`/main/${encodeURIComponent(user.email)}/bookings`);
      void result;
    } catch (e) {
      toast.error(e.message || "Could not complete payment");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="container py-5 text-center">
        <p className="text-muted">Loading checkout…</p>
      </div>
    );
  }

  if (error || !payment) {
    return (
      <div className="container py-5">
        <div className="alert alert-danger">{error || "Payment not found"}</div>
      </div>
    );
  }

  if (payment.status !== "pending") {
    return (
      <div className="container py-5" style={{ maxWidth: 480 }}>
        <div className="card shadow-card">
          <div className="card-body text-center">
            <h5 className="card-title">This payment is already {payment.status}</h5>
            <p className="text-muted small">Nothing more to do here.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container py-5" style={{ maxWidth: 480 }}>
      <div className="card shadow-card">
        <div className="card-body">
          <div className="d-flex align-items-center gap-2 mb-3">
            <span className="badge bg-secondary">DEMO CHECKOUT</span>
            <span className="small text-muted">Simulated payment — no real money moves</span>
          </div>
          <h4 className="card-title">{payment.schedule_title || "Booking payment"}</h4>
          <p className="display-6 fw-bold mb-4">
            {payment.currency} {payment.amount}
          </p>
          <div className="d-grid gap-2">
            <button
              className="btn btn-success btn-lg"
              disabled={submitting}
              onClick={() => resolve("succeeded")}
            >
              {submitting ? "Processing…" : "Pay now"}
            </button>
            <button
              className="btn btn-outline-danger"
              disabled={submitting}
              onClick={() => resolve("failed")}
            >
              Simulate declined payment
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
