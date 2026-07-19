// frontend/src/components/ProfileEditor.jsx
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

export default function ProfileEditor() {
  const { token, user: sessionUser, refreshMe } = useAuth();
  const [me, setMe] = useState(null);
  const [companyInfo, setCompanyInfo] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("basic");
  const [hasChanges, setHasChanges] = useState(false);
  const [originalData, setOriginalData] = useState(null);

  const roleBucket = useMemo(() => {
    const r = (me?.role || sessionUser?.role || "user").toLowerCase();
    const hasFiscalId =
      !!me?.fiscal_data?.tax_identification?.primary_identification_number &&
      me.fiscal_data.tax_identification.primary_identification_number.trim() !== "";
    if (r === "guide" && hasFiscalId) return "enterprise_guide";
    if (r === "guide") return "guide";
    return "user";
  }, [me, sessionUser]);

  // ✅ Cargar info de empresa
  useEffect(() => {
    if (!token || me?.role !== "guide") return;

    api
      .get("/users/me/company-info")
      .then(data => setCompanyInfo(data))
      .catch(() => {});
  }, [token, me?.role]);

  useEffect(() => {
    let ignore = false;
    (async () => {
      if (!token) return;
      const data = await api.get("/users/me").catch(() => null);
      if (!data) return;
      if (!ignore) {
        const normalized = normalizeMe(data);
        setMe(normalized);
        setOriginalData(JSON.stringify(normalized));
      }
    })();
    return () => { ignore = true; };
  }, [token]);

  const normalizeMe = (m) => {
    const fd = (m?.fiscal_data && typeof m.fiscal_data === "object") ? m.fiscal_data : {};
    return {
      ...m,
      profile: (m?.profile && typeof m.profile === "object") ? m.profile : {},
      fiscal_data: {
        metadata: { ...(fd.metadata || {}) },
        tax_location: { tax_address: { ...(fd.tax_location?.tax_address || {}) } },
        international: { ...(fd.international || {}) },
        basic_information: { ...(fd.basic_information || {}) },
        economic_activity: { ...(fd.economic_activity || {}) },
        tax_identification: { ...(fd.tax_identification || {}) },
        legal_representation: {
          legal_representative: { ...(fd.legal_representation?.legal_representative || {}) },
          tax_contact: { ...(fd.legal_representation?.tax_contact || {}) },
        },
        financial_information: { 
          ...(fd.financial_information || {}),
          bank_account: fd.financial_information?.bank_account || {
            bank_name: "",
            account_holder: "",
            account_number: "",
            account_type: "",
            routing_number: "",
            swift_code: ""
          }
        },
      },
    };
  };

  // ✅ Detectar cambios
  useEffect(() => {
    if (!originalData || !me) return;
    const currentData = JSON.stringify(me);
    setHasChanges(originalData !== currentData);
    setSaveSuccess(false); // Reset success message on any change
  }, [me, originalData]);

  const setField = (k, v) => {
    setMe((prev) => ({ ...(prev || {}), [k]: v }));
  };
  
  const setProfileField = (k, v) =>
    setMe((prev) => ({ ...(prev || {}), profile: { ...(prev?.profile || {}), [k]: v } }));

  const setFiscalPath = (path, value) =>
    setMe((prev) => {
      const next = { ...(prev || {}), fiscal_data: { ...(prev?.fiscal_data || {}) } };
      let node = next.fiscal_data;
      for (let i = 0; i < path.length - 1; i++) {
        const k = path[i];
        node[k] = { ...(node[k] || {}) };
        node = node[k];
      }
      node[path[path.length - 1]] = value;
      return next;
    });

  const handleSave = async () => {
    setError("");
    setSaving(true);
    setSaveSuccess(false);

    try {
      const payload = { ...me };
      delete payload.created_at;
      delete payload.updated_at;
      delete payload.id;
      delete payload.email;

      const updated = await api.patch("/users/me", payload);
      const normalized = normalizeMe(updated);
      setMe(normalized);
      setOriginalData(JSON.stringify(normalized));
      setSaveSuccess(true);
      await refreshMe();
      
      // Auto-hide success message after 3 seconds
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (!me) return <div className="p-4">Loading...</div>;

  return (
    <div className="container-fluid py-4">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-10">
          <div className="card shadow-card rounded-xl2">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center mb-4">
                <h2 className="text-h2 mb-0">Profile Settings</h2>
                <div className="d-flex gap-2 align-items-center">
                  {saveSuccess && (
                    <div className="alert alert-success mb-0 py-2 px-3">
                      ✓ Changes saved successfully
                    </div>
                  )}
                  <button
                    className="btn btn-primary"
                    onClick={handleSave}
                    disabled={saving || !hasChanges}
                  >
                    {saving ? "Saving..." : hasChanges ? "Save Changes" : "Saved"}
                  </button>
                </div>
              </div>

              {error && <div className="alert alert-danger">{error}</div>}

              {/* Company Info Banner for Guides */}
              {me.role === "guide" && companyInfo && (
                <div className="alert alert-info mb-4">
                  <div className="d-flex justify-content-between align-items-start">
                    <div>
                      <h6 className="fw-bold mb-1">
                        {companyInfo.type === "company_member" ? "Company Member" : "Independent Guide"}
                      </h6>
                      {companyInfo.type === "company_member" ? (
                        <div>
                          <div><strong>Company:</strong> {companyInfo.company_name}</div>
                          <div><strong>Position:</strong> {companyInfo.position}</div>
                          {companyInfo.is_admin && <span className="badge bg-primary">Admin</span>}
                        </div>
                      ) : (
                        <div>Operating as independent guide</div>
                      )}
                    </div>
                    {companyInfo.type === "company_member" && (
                      <button 
                        className="btn btn-sm btn-outline-primary"
                        onClick={() => window.location.href = `/main/${sessionUser.email}/companies`}
                      >
                        Manage Company
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Tabs */}
              <ul className="nav nav-tabs mb-4">
                <li className="nav-item">
                  <button
                    className={`nav-link ${tab === "basic" ? "active" : ""}`}
                    onClick={() => setTab("basic")}
                  >
                    Basic Info
                  </button>
                </li>
                {(roleBucket === "guide" || roleBucket === "enterprise_guide") && (
                  <li className="nav-item">
                    <button
                      className={`nav-link ${tab === "fiscal" ? "active" : ""}`}
                      onClick={() => setTab("fiscal")}
                    >
                      Fiscal Data
                    </button>
                  </li>
                )}
              </ul>

              {/* Basic Info Tab */}
              {tab === "basic" && (
                <div className="row g-3">
                  <div className="col-12 col-md-6">
                    <label className="form-label">Display Name</label>
                    <input
                      className="form-control"
                      value={me.display_name || ""}
                      onChange={(e) => setField("display_name", e.target.value)}
                    />
                  </div>
                  <div className="col-12 col-md-6">
                    <label className="form-label">Email</label>
                    <input className="form-control" value={me.email || ""} disabled />
                  </div>
                  <div className="col-12 col-md-6">
                    <label className="form-label">First Name</label>
                    <input
                      className="form-control"
                      value={me.first_name || ""}
                      onChange={(e) => setField("first_name", e.target.value)}
                    />
                  </div>
                  <div className="col-12 col-md-6">
                    <label className="form-label">Last Name</label>
                    <input
                      className="form-control"
                      value={me.last_name || ""}
                      onChange={(e) => setField("last_name", e.target.value)}
                    />
                  </div>
                  <div className="col-12 col-md-6">
                    <label className="form-label">Phone</label>
                    <input
                      className="form-control"
                      value={me.phone || ""}
                      onChange={(e) => setField("phone", e.target.value)}
                    />
                  </div>
                  <div className="col-12 col-md-6">
                    <label className="form-label">Birth Date</label>
                    <input
                      type="date"
                      className="form-control"
                      value={me.birth_date || ""}
                      onChange={(e) => setField("birth_date", e.target.value)}
                    />
                  </div>
                </div>
              )}

              {/* Fiscal Data Tab */}
              {tab === "fiscal" && (
                <div className="row g-3">
                  <div className="col-12">
                    <h5 className="fw-semibold mb-3">Bank Account Information</h5>
                    <div className="alert alert-info">
                      <small>
                        <strong>Required for payments:</strong> Please provide your bank account details 
                        where you wish to receive payments for bookings. All information is encrypted and secure.
                      </small>
                    </div>
                  </div>

                  <div className="col-12 col-md-6">
                    <label className="form-label">Bank Name *</label>
                    <input
                      className="form-control"
                      placeholder="e.g., Bank of America"
                      value={me.fiscal_data?.financial_information?.bank_account?.bank_name || ""}
                      onChange={(e) =>
                        setFiscalPath(
                          ["financial_information", "bank_account", "bank_name"],
                          e.target.value
                        )
                      }
                    />
                  </div>

                  <div className="col-12 col-md-6">
                    <label className="form-label">Account Holder Name *</label>
                    <input
                      className="form-control"
                      placeholder="Full name as appears on account"
                      value={me.fiscal_data?.financial_information?.bank_account?.account_holder || ""}
                      onChange={(e) =>
                        setFiscalPath(
                          ["financial_information", "bank_account", "account_holder"],
                          e.target.value
                        )
                      }
                    />
                  </div>

                  <div className="col-12 col-md-6">
                    <label className="form-label">Account Number *</label>
                    <input
                      className="form-control"
                      type="password"
                      placeholder="••••••••"
                      value={me.fiscal_data?.financial_information?.bank_account?.account_number || ""}
                      onChange={(e) =>
                        setFiscalPath(
                          ["financial_information", "bank_account", "account_number"],
                          e.target.value
                        )
                      }
                    />
                  </div>

                  <div className="col-12 col-md-6">
                    <label className="form-label">Account Type</label>
                    <select
                      className="form-select"
                      value={me.fiscal_data?.financial_information?.bank_account?.account_type || ""}
                      onChange={(e) =>
                        setFiscalPath(
                          ["financial_information", "bank_account", "account_type"],
                          e.target.value
                        )
                      }
                    >
                      <option value="">Select...</option>
                      <option value="checking">Checking</option>
                      <option value="savings">Savings</option>
                    </select>
                  </div>

                  <div className="col-12 col-md-6">
                    <label className="form-label">Routing Number (US) / Sort Code (UK)</label>
                    <input
                      className="form-control"
                      placeholder="9 digits (US) or 6 digits (UK)"
                      value={me.fiscal_data?.financial_information?.bank_account?.routing_number || ""}
                      onChange={(e) =>
                        setFiscalPath(
                          ["financial_information", "bank_account", "routing_number"],
                          e.target.value
                        )
                      }
                    />
                  </div>

                  <div className="col-12 col-md-6">
                    <label className="form-label">SWIFT/BIC Code (International)</label>
                    <input
                      className="form-control"
                      placeholder="For international transfers"
                      value={me.fiscal_data?.financial_information?.bank_account?.swift_code || ""}
                      onChange={(e) =>
                        setFiscalPath(
                          ["financial_information", "bank_account", "swift_code"],
                          e.target.value
                        )
                      }
                    />
                  </div>

                  {roleBucket === "enterprise_guide" && (
                    <>
                      <div className="col-12 mt-4">
                        <h5 className="fw-semibold mb-3">Tax Information</h5>
                      </div>
                      <div className="col-12 col-md-6">
                        <label className="form-label">Tax ID</label>
                        <input
                          className="form-control"
                          value={me.tax_id || ""}
                          onChange={(e) => setField("tax_id", e.target.value)}
                        />
                      </div>
                      <div className="col-12 col-md-6">
                        <label className="form-label">Primary Identification Number</label>
                        <input
                          className="form-control"
                          value={
                            me.fiscal_data?.tax_identification?.primary_identification_number || ""
                          }
                          onChange={(e) =>
                            setFiscalPath(
                              ["tax_identification", "primary_identification_number"],
                              e.target.value
                            )
                          }
                        />
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}