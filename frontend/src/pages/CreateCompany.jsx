// frontend/src/pages/CreateCompany.jsx
import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";

export default function CreateCompany() {
  const { user } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    name: "",
    legal_name: "",
    trade_name: "",
    description: "",
    entity_type: "",
    incorporation_date: "",
    country: "",
    currency: "USD",
    address: "",
    legal_representive: "",
    legal_representive_text: "",
    legal_representive_phone: "",
    is_multinational: false,
  });

  const setField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    // Validation
    if (!form.name || !form.legal_name || !form.entity_type) {
      setError("Name, legal name, and entity type are required");
      setSubmitting(false);
      return;
    }

    try {
      const company = await api.post("/companies", form);
      toast.success("Company created successfully!");
      navigate(`/main/${encodeURIComponent(user.email)}/company/${company.id}`);
    } catch (err) {
      setError(err.message || "Failed to create company");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container py-4">
      <div className="card shadow-card rounded-xl2">
        <div className="card-body">
          <h2 className="text-h2 mb-4">Create Company</h2>
          <p className="text-muted mb-4">
            Register your tourism company to manage guides and activities.
            Free tier includes up to 5 guides.
          </p>

          {error && <div className="alert alert-danger">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="row g-3">
              {/* Basic Information */}
              <div className="col-12">
                <h5 className="fw-semibold">Basic Information</h5>
              </div>

              <div className="col-md-6">
                <label className="form-label">Company Name *</label>
                <input
                  className="form-control"
                  value={form.name}
                  onChange={(e) => setField("name", e.target.value)}
                  required
                />
              </div>

              <div className="col-md-6">
                <label className="form-label">Legal Name *</label>
                <input
                  className="form-control"
                  value={form.legal_name}
                  onChange={(e) => setField("legal_name", e.target.value)}
                  required
                />
              </div>

              <div className="col-md-6">
                <label className="form-label">Trade Name</label>
                <input
                  className="form-control"
                  value={form.trade_name}
                  onChange={(e) => setField("trade_name", e.target.value)}
                />
              </div>

              <div className="col-md-6">
                <label className="form-label">Entity Type *</label>
                <select
                  className="form-select"
                  value={form.entity_type}
                  onChange={(e) => setField("entity_type", e.target.value)}
                  required
                >
                  <option value="">Select...</option>
                  <option value="sole_proprietorship">Sole Proprietorship</option>
                  <option value="llc">LLC</option>
                  <option value="corporation">Corporation</option>
                  <option value="partnership">Partnership</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="col-12">
                <label className="form-label">Description</label>
                <textarea
                  className="form-control"
                  rows={3}
                  value={form.description}
                  onChange={(e) => setField("description", e.target.value)}
                  placeholder="Describe your company and services..."
                />
              </div>

              {/* Legal Information */}
              <div className="col-12 mt-4">
                <h5 className="fw-semibold">Legal Information</h5>
              </div>

              <div className="col-md-6">
                <label className="form-label">Incorporation Date</label>
                <input
                  type="date"
                  className="form-control"
                  value={form.incorporation_date}
                  onChange={(e) => setField("incorporation_date", e.target.value)}
                />
              </div>

              <div className="col-md-6">
                <label className="form-label">Country *</label>
                <input
                  className="form-control"
                  value={form.country}
                  onChange={(e) => setField("country", e.target.value)}
                  required
                />
              </div>

              <div className="col-md-6">
                <label className="form-label">Currency</label>
                <select
                  className="form-select"
                  value={form.currency}
                  onChange={(e) => setField("currency", e.target.value)}
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                  <option value="CLP">CLP</option>
                  <option value="ARS">ARS</option>
                  <option value="BRL">BRL</option>
                </select>
              </div>

              <div className="col-md-6">
                <label className="form-label">Address *</label>
                <input
                  className="form-control"
                  value={form.address}
                  onChange={(e) => setField("address", e.target.value)}
                  required
                />
              </div>

              {/* Legal Representative */}
              <div className="col-12 mt-4">
                <h5 className="fw-semibold">Legal Representative</h5>
              </div>

              <div className="col-md-4">
                <label className="form-label">Name *</label>
                <input
                  className="form-control"
                  value={form.legal_representive}
                  onChange={(e) => setField("legal_representive", e.target.value)}
                  required
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">ID/Tax Number *</label>
                <input
                  className="form-control"
                  value={form.legal_representive_text}
                  onChange={(e) => setField("legal_representive_text", e.target.value)}
                  required
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">Phone *</label>
                <input
                  className="form-control"
                  value={form.legal_representive_phone}
                  onChange={(e) => setField("legal_representive_phone", e.target.value)}
                  required
                />
              </div>

              <div className="col-12">
                <div className="form-check">
                  <input
                    id="multinational"
                    type="checkbox"
                    className="form-check-input"
                    checked={form.is_multinational}
                    onChange={(e) => setField("is_multinational", e.target.checked)}
                  />
                  <label htmlFor="multinational" className="form-check-label">
                    Multinational Company
                  </label>
                </div>
              </div>
            </div>

            <div className="d-flex gap-2 mt-4">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => navigate(-1)}
                disabled={submitting}
              >
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? "Creating..." : "Create Company"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}