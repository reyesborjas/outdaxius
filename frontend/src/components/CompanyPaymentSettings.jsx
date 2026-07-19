// frontend/src/components/CompanyPaymentSettings.jsx
import { useEffect, useState } from "react";
import { api } from "../lib/api";

const PROVIDER_CREDENTIAL_FIELDS = {
  flow: [
    { key: "api_key", label: "API Key" },
    { key: "secret_key", label: "Secret Key" },
  ],
  stripe: [{ key: "secret_key", label: "Secret Key" }],
  transbank: [
    { key: "commerce_code", label: "Commerce Code" },
    { key: "api_key", label: "API Key" },
  ],
  mercadopago: [{ key: "access_token", label: "Access Token" }],
};

export default function CompanyPaymentSettings({ companyId, token }) {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [provider, setProvider] = useState("flow");
  const [isSandbox, setIsSandbox] = useState(true);
  const [currency, setCurrency] = useState("CLP");
  const [credentialValues, setCredentialValues] = useState({});

  const loadAccounts = () => {
    if (!companyId || !token) return;
    setLoading(true);
    api
      .get(`/companies/${companyId}/payment-accounts`)
      .then((data) => {
        setAccounts(data);
        setError("");
      })
      .catch(() => setError("Could not load payment accounts"))
      .finally(() => setLoading(false));
  };

  useEffect(loadAccounts, [companyId, token]);

  const handleCredentialChange = (key, value) => {
    setCredentialValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.post(`/companies/${companyId}/payment-accounts`, {
        provider,
        is_sandbox: isSandbox,
        currency,
        credentials: credentialValues,
      });
      setCredentialValues({});
      loadAccounts();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleVerify = async (accountId) => {
    setError("");
    try {
      await api.post(`/companies/${companyId}/payment-accounts/${accountId}/verify`);
      loadAccounts();
    } catch (err) {
      setError(err.message);
    }
  };

  const fields = PROVIDER_CREDENTIAL_FIELDS[provider] || [];

  return (
    <div className="card shadow-card mb-4">
      <div className="card-body">
        <h5 className="card-title mb-3">Payment Accounts</h5>
        <p className="text-muted small">
          This company is its own merchant of record — Outdaxius never holds funds. A schedule
          cannot be published for sale until an account here is verified.
        </p>

        {error && <div className="alert alert-danger">{error}</div>}

        {loading ? (
          <div className="text-center py-3">
            <div className="spinner-border spinner-border-sm" role="status" />
          </div>
        ) : (
          <table className="table table-sm">
            <thead>
              <tr>
                <th>Provider</th>
                <th>Mode</th>
                <th>Currency</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {accounts.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-muted">No payment accounts configured yet.</td>
                </tr>
              )}
              {accounts.map((acc) => (
                <tr key={acc.id}>
                  <td className="text-capitalize">{acc.provider}</td>
                  <td>{acc.is_sandbox ? "Sandbox" : "Production"}</td>
                  <td>{acc.currency}</td>
                  <td>
                    {acc.charges_enabled ? (
                      <span className="badge bg-success">Charges enabled</span>
                    ) : (
                      <span className="badge bg-warning">Not verified</span>
                    )}
                  </td>
                  <td>
                    {!acc.charges_enabled && acc.is_sandbox && (
                      <button
                        className="btn btn-sm btn-outline-primary"
                        onClick={() => handleVerify(acc.id)}
                      >
                        Verify (sandbox)
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <hr />

        <h6 className="mb-3">Add / update a provider</h6>
        <form onSubmit={handleSubmit}>
          <div className="row g-3">
            <div className="col-md-4">
              <label className="form-label">Provider</label>
              <select
                className="form-select"
                value={provider}
                onChange={(e) => { setProvider(e.target.value); setCredentialValues({}); }}
              >
                <option value="flow">Flow</option>
                <option value="stripe">Stripe</option>
                <option value="transbank">Transbank</option>
                <option value="mercadopago">Mercado Pago</option>
              </select>
            </div>
            <div className="col-md-4">
              <label className="form-label">Currency</label>
              <input
                className="form-control"
                maxLength={3}
                value={currency}
                onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              />
            </div>
            <div className="col-md-4 d-flex align-items-end">
              <div className="form-check">
                <input
                  className="form-check-input"
                  type="checkbox"
                  id="isSandbox"
                  checked={isSandbox}
                  onChange={(e) => setIsSandbox(e.target.checked)}
                />
                <label className="form-check-label" htmlFor="isSandbox">Sandbox mode</label>
              </div>
            </div>

            {fields.map((f) => (
              <div className="col-md-6" key={f.key}>
                <label className="form-label">{f.label}</label>
                <input
                  type="password"
                  className="form-control"
                  value={credentialValues[f.key] || ""}
                  onChange={(e) => handleCredentialChange(f.key, e.target.value)}
                  required
                />
              </div>
            ))}
          </div>

          <button type="submit" className="btn btn-primary mt-3" disabled={saving}>
            {saving ? "Saving..." : "Save credentials"}
          </button>
        </form>
      </div>
    </div>
  );
}
