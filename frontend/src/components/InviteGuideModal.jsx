// frontend/src/components/InviteGuideModal.jsx

import { useState } from "react";

export default function InviteGuideModal({ companyId, onClose, onSuccess }) {
  const [email, setEmail] = useState("");
  const [expires, setExpires] = useState(7);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const token = localStorage.getItem("token");
      const res = await fetch(
        `http://localhost:8000/api/companies/${companyId}/invitations`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            invited_email: email,
            expires_in_days: expires,
          }),
        }
      );

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to create invitation");
      }

      const invitation = await res.json();
      
      // Show success with invitation link
      const link = `${window.location.origin}/accept-invitation?code=${invitation.code}`;
      
      alert(`✅ Invitation created!\n\nShare this link with the guide:\n${link}`);
      
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal show d-block" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Invite Guide to Company</h5>
            <button className="btn-close" onClick={onClose}></button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              {error && (
                <div className="alert alert-danger">{error}</div>
              )}

              <div className="mb-3">
                <label className="form-label">Guide Email *</label>
                <input
                  type="email"
                  className="form-control"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="guide@example.com"
                  required
                />
                <div className="form-text">
                  The guide must have an account with role "guide"
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label">Expires In</label>
                <select
                  className="form-select"
                  value={expires}
                  onChange={(e) => setExpires(Number(e.target.value))}
                >
                  <option value={3}>3 days</option>
                  <option value={7}>7 days (recommended)</option>
                  <option value={14}>14 days</option>
                  <option value={30}>30 days</option>
                </select>
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onClose}
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
              >
                {loading ? "Creating..." : "Send Invitation"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}