// frontend/src/components/CancellationRateBadge.jsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

export function tierForRate(rate) {
  if (rate <= 0.05) return { label: "Reliable", badgeClass: "bg-success-subtle text-success-emphasis", textClass: "text-success" };
  if (rate <= 0.15) return { label: "Some cancellations", badgeClass: "bg-warning-subtle text-warning-emphasis", textClass: "text-warning" };
  return { label: "Frequent cancellations", badgeClass: "bg-danger-subtle text-danger-emphasis", textClass: "text-danger" };
}

export default function CancellationRateBadge({ companyId, className = "" }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!companyId) return;
    let alive = true;
    api
      .get(`/companies/${companyId}/cancellation-rate`, { skipAuth: true })
      .then((d) => alive && setData(d))
      .catch(() => alive && setData(null));
    return () => {
      alive = false;
    };
  }, [companyId]);

  if (!companyId || !data) return null;

  return (
    <Link
      to={`/companies/${companyId}`}
      className="text-decoration-none"
      onClick={(e) => e.stopPropagation()}
    >
      {data.sufficient_data ? (
        <span
          className={`badge ${tierForRate(data.cancellation_rate).badgeClass} ${className}`}
          title={`${data.vendor_cancellations} vendor cancellations of ${data.total_bookings} bookings in the last ${data.window_days} days`}
        >
          {Math.round(data.cancellation_rate * 100)}% cancellation rate
        </span>
      ) : (
        <span
          className={`badge bg-secondary-subtle text-secondary-emphasis ${className}`}
          title="Not enough recent bookings yet to publish a cancellation rate"
        >
          New vendor
        </span>
      )}
    </Link>
  );
}
