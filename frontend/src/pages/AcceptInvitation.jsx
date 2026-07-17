import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCompany } from "../hooks/useCompany";

export default function AcceptInvitation() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const { acceptInvitation } = useCompany(null);

  const [code, setCode] = useState(searchParams.get("code") || "");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState(null);

  // Manejo directo si hay código por URL al cargar
  useEffect(() => {
    if (searchParams.get("code")) {
      handleAccept();
    }
    // eslint-disable-next-line
  }, []);

  async function handleAccept(e) {
    if (e) e.preventDefault();
    if (!code) {
      setError("No invitation code provided.");
      return;
    }
    setSubmitting(true);
    setSuccess(null);
    setError(null);
    try {
      await acceptInvitation(code);
      setSuccess("Invitation accepted! Redirecting...");
      setTimeout(() => {
        navigate("/main");
      }, 1500);
    } catch (err) {
      setError(err.message || "Failed to accept invitation.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="container py-5">
      <div className="card shadow-card p-4 mx-auto" style={{maxWidth: 480}}>
        <h2 className="mb-3">Accept Invitation</h2>
        <form onSubmit={handleAccept}>
          <div className="mb-3">
            <label htmlFor="code" className="form-label">Invitation Code</label>
            <input
              type="text"
              id="code"
              className="form-control"
              value={code}
              onChange={e => setCode(e.target.value)}
              disabled={submitting}
              required
            />
          </div>
          {error && <div className="alert alert-danger">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}
          <button className="btn btn-primary" type="submit" disabled={submitting || !code}>
            {submitting ? "Processing..." : "Accept Invitation"}
          </button>
        </form>
        <button
          className="btn btn-link mt-3"
          onClick={() => navigate("/main")}
          disabled={submitting}
        >
          Back to Dashboard
        </button>
      </div>
    </div>
  );
}
