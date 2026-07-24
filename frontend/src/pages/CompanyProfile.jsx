// frontend/src/pages/CompanyProfile.jsx
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import { tierForRate } from "../components/CancellationRateBadge";

export default function CompanyProfile() {
  const { companyId } = useParams();
  const [company, setCompany] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    api
      .get(`/companies/${companyId}/public`, { skipAuth: true })
      .then((d) => alive && setCompany(d))
      .catch((e) => alive && setError(e.message || "Company not found"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [companyId]);

  if (loading) {
    return (
      <div className="container py-4">
        <p className="text-muted">Loading…</p>
      </div>
    );
  }

  if (error || !company) {
    return (
      <div className="container py-4">
        <div className="alert alert-danger">{error || "Company not found"}</div>
      </div>
    );
  }

  const { cancellation } = company;

  return (
    <div className="container py-4" style={{ maxWidth: 720 }}>
      <h2 className="text-h1 mb-1">{company.name}</h2>
      {company.trade_name && company.trade_name !== company.name && (
        <p className="text-muted mb-2">{company.trade_name}</p>
      )}
      {company.country && <p className="small text-muted mb-3">Based in {company.country}</p>}
      {company.description && <p className="mb-4">{company.description}</p>}

      <div className="card shadow-card">
        <div className="card-body">
          <h5 className="card-title">Vendor reliability</h5>
          {cancellation.sufficient_data ? (
            <>
              <p className={`fs-4 fw-bold mb-1 ${tierForRate(cancellation.cancellation_rate).textClass}`}>
                {Math.round(cancellation.cancellation_rate * 100)}% cancellation rate
              </p>
              <p className="text-muted small mb-0">
                {cancellation.vendor_cancellations} of {cancellation.total_bookings} bookings were
                cancelled by this vendor in the last {cancellation.window_days} days.
              </p>
            </>
          ) : (
            <p className="text-muted mb-0">
              Not enough recent bookings yet ({cancellation.total_bookings}) to publish a
              cancellation rate.
            </p>
          )}
        </div>
      </div>

      <Link to="/activities" className="btn btn-outline-secondary mt-3">
        Browse activities
      </Link>
    </div>
  );
}
