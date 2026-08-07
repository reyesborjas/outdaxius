// frontend/src/pages/Register.jsx
import React, { useMemo, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../lib/api";

const preventEnterSubmit = (e) => {
  if (e.key === "Enter") e.preventDefault();
};

export default function Register() {
  const navigate = useNavigate();

  const [activeStep, setActiveStep] = useState(0);
  const [role, setRole] = useState(null);
  const [guideType, setGuideType] = useState(null);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    email: "",
    password: "",
    display_name: "",
    first_name: "",
    last_name: "",
    passport_number: "",
    phone: "",
    profile: "",
    tax_id: "",
    fiscal_data: {
      tax_identification: {
        primary_identification_number: "",
        identification_type: "",
      },
      basic_information: {
        legal_name: "",
        trade_name: "",
        entity_type: "",
        incorporation_date: "",
        incorporation_country: "",
        active_status: false,
      },
      economic_activity: {
        economic_activity_code: "",
        activity_description: "",
      },
      tax_location: {
        tax_address: {
          address: "",
          city: "",
          state_province: "",
          postal_code: "",
          country: "",
        },
      },
      legal_representation: {
        legal_representative: {
          name: "",
          identification: "",
          position: "",
        },
        tax_contact: {
          name: "",
          email: "",
          phone: "",
        },
      },
      financial_information: { functional_currency: "" },
      international: { is_multinational: false, operating_countries: [] },
      metadata: {
        creation_date: new Date().toISOString(),
        last_update_date: new Date().toISOString(),
        verified: false,
      },
    },
  });

  const setField = useCallback((name, value) => {
    setForm((prev) => ({ ...prev, [name]: value }));
  }, []);

  const setFiscal = useCallback((path, value) => {
    setForm((prev) => {
      const next = { ...prev, fiscal_data: { ...prev.fiscal_data } };
      let node = next.fiscal_data;
      for (let i = 0; i < path.length - 1; i++) {
        const k = path[i];
        node[k] = Array.isArray(node[k]) ? [...node[k]] : { ...node[k] };
        node = node[k];
      }
      node[path[path.length - 1]] = value;
      return next;
    });
  }, []);

  const next = () => setActiveStep((s) => s + 1);
  const back = () => setActiveStep((s) => Math.max(0, s - 1));

  // Every step lives inside one <form> and is hidden with display:none rather than unmounted, so
  // a hidden step's inputs are STILL part of the form's constraint-validation set. A `required`
  // input inside a hidden section makes the form permanently invalid: on submit the browser tries
  // to focus it to show the validation bubble, cannot (it has no layout box), logs
  // "An invalid form control with name='' is not focusable", and silently refuses to submit.
  // handleSubmit never runs and the user sees nothing happen.
  //
  // These flags are the single source of truth for each step: they drive display, aria-hidden and
  // `required` together, so a field can only be required while it is actually on screen.
  const isStepRole = activeStep === 0;
  const isStepBasic = activeStep === 1;
  const isStepGuideType = activeStep === 2 && role === "guide";
  const isStepIndependent = activeStep === 3 && guideType === "independent";
  const isStepCompany = activeStep === 3 && guideType === "company";
  const isStepUserSubmit = activeStep === 2 && role === "user";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!role) return setError("Select a role.");
    if (!form.email || !form.password || !form.display_name)
      return setError("Email, password, and display name are required.");

    const payload = {
      email: form.email,
      password: form.password,
      display_name: form.display_name,
      first_name: form.first_name || null,
      last_name: form.last_name || null,
      role: role === "guide" ? "guide" : "client",
    };

    if (role === "guide") {
      if (guideType === "independent") {
        payload.passport_number = form.passport_number || null;
        payload.phone = form.phone || null;
        payload.profile = form.profile ? { about: form.profile } : {};
      }
      if (guideType === "company") {
        payload.tax_id = form.tax_id || null;
        payload.fiscal_data = form.fiscal_data;
      }
    }

    try {
      await api.post("/auth/register", payload, { skipAuth: true });
      navigate("/login");
    } catch (err) {
      let msg = "Registration failed";
      if (err instanceof ApiError && Array.isArray(err.detail?.detail)) {
        msg = err.detail.detail.map((d) => d.msg).join(", ");
      } else if (err instanceof ApiError) {
        msg = err.message;
      } else {
        msg = "Network error. Try again.";
      }
      setError(msg);
    }
  };

  const StepRole = useMemo(
    () => (
      <section aria-hidden={!isStepRole} style={{ display: isStepRole ? "block" : "none" }}>
        <h3 className="mb-3">What do you want to do at Outdaxious?</h3>
        <div className="vstack gap-2">
          <button
            type="button"
            className={`btn ${role === "user" ? "btn-primary" : "btn-outline-primary"}`}
            onClick={() => {
              setRole("user");
              setActiveStep(1);
            }}
          >
            I want to be a traveler (participant)
          </button>
          <button
            type="button"
            className={`btn ${role === "guide" ? "btn-secondary" : "btn-outline-secondary"}`}
            onClick={() => {
              setRole("guide");
              setActiveStep(1);
            }}
          >
            I want to be a travel activity guide
          </button>
        </div>
      </section>
    ),
    [isStepRole, role]
  );

  const StepBasic = useMemo(
    () => (
      <section aria-hidden={!isStepBasic} style={{ display: isStepBasic ? "block" : "none" }}>
        <h3 className="mb-3">Basic Information</h3>
        <div className="mb-2">
          <label className="form-label">Display Name</label>
          <input
            name="display_name"
            autoComplete="name"
            className="form-control"
            value={form.display_name}
            onKeyDown={preventEnterSubmit}
            onChange={(e) => setField("display_name", e.target.value)}
            required={isStepBasic}
          />
        </div>
        <div className="row g-2">
          <div className="col-12 col-md-6">
            <label className="form-label">First Name</label>
            <input
              name="first_name"
              className="form-control"
              value={form.first_name}
              onKeyDown={preventEnterSubmit}
              onChange={(e) => setField("first_name", e.target.value)}
            />
          </div>
          <div className="col-12 col-md-6">
            <label className="form-label">Last Name</label>
            <input
              name="last_name"
              className="form-control"
              value={form.last_name}
              onKeyDown={preventEnterSubmit}
              onChange={(e) => setField("last_name", e.target.value)}
            />
          </div>
        </div>
        <div className="mb-2">
          <label className="form-label">Email</label>
          <input
            name="email"
            type="email"
            autoComplete="email"
            className="form-control"
            value={form.email}
            onKeyDown={preventEnterSubmit}
            onChange={(e) => setField("email", e.target.value)}
            required={isStepBasic}
          />
        </div>
        <div className="mb-2">
          <label className="form-label">Password</label>
          <input
            name="password"
            type="password"
            autoComplete="new-password"
            className="form-control"
            value={form.password}
            onKeyDown={preventEnterSubmit}
            onChange={(e) => setField("password", e.target.value)}
            required={isStepBasic}
          />
        </div>
        <div className="d-flex justify-content-between mt-3">
          <button type="button" className="btn btn-secondary" onClick={back}>
            Back
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={next}
            disabled={!form.email || !form.password || !form.display_name}
          >
            Next
          </button>
        </div>
      </section>
    ),
    [isStepBasic, form, setField]
  );

  const StepGuideType = useMemo(
    () => (
      <section aria-hidden={!isStepGuideType} style={{ display: isStepGuideType ? "block" : "none" }}>
        <h3 className="mb-3">Are you independent or a company?</h3>
        <div className="vstack gap-2">
          <button
            type="button"
            className={`btn ${guideType === "independent" ? "btn-primary" : "btn-outline-primary"}`}
            onClick={() => {
              setGuideType("independent");
              setActiveStep(3);
            }}
          >
            Independent Guide
          </button>
          <button
            type="button"
            className={`btn ${guideType === "company" ? "btn-secondary" : "btn-outline-secondary"}`}
            onClick={() => {
              setGuideType("company");
              setActiveStep(3);
            }}
          >
            Company
          </button>
        </div>
        <div className="d-flex justify-content-between mt-3">
          <button type="button" className="btn btn-secondary" onClick={back}>
            Back
          </button>
        </div>
      </section>
    ),
    [isStepGuideType, guideType]
  );

  const StepIndependent = useMemo(
    () => (
      <section aria-hidden={!isStepIndependent} style={{ display: isStepIndependent ? "block" : "none" }}>
        <h3 className="mb-3">Independent Guide</h3>
        <div className="mb-2">
          <label className="form-label">Passport Number</label>
          <input
            name="passport_number"
            className="form-control"
            value={form.passport_number}
            onKeyDown={preventEnterSubmit}
            onChange={(e) => setField("passport_number", e.target.value)}
          />
        </div>
        <div className="mb-2">
          <label className="form-label">Phone</label>
          <input
            name="phone"
            className="form-control"
            value={form.phone}
            onKeyDown={preventEnterSubmit}
            onChange={(e) => setField("phone", e.target.value)}
          />
        </div>
        <div className="mb-2">
          <label className="form-label">Profile / About you</label>
          <textarea
            name="profile"
            className="form-control"
            rows={4}
            value={form.profile}
            onKeyDown={preventEnterSubmit}
            onChange={(e) => setField("profile", e.target.value)}
          />
        </div>
        <div className="d-flex justify-content-between mt-3">
          <button type="button" className="btn btn-secondary" onClick={back}>
            Back
          </button>
          <button type="submit" className="btn btn-primary">
            Register
          </button>
        </div>
      </section>
    ),
    [isStepIndependent, form, setField]
  );

  const StepCompany = useMemo(
    () => (
      <section aria-hidden={!isStepCompany} style={{ display: isStepCompany ? "block" : "none" }}>
        <h3 className="mb-3">Company Fiscal Information</h3>

        <div className="mb-2">
          <label className="form-label">Tax ID *</label>
          <input
            name="tax_id"
            className="form-control"
            value={form.tax_id}
            onKeyDown={preventEnterSubmit}
            onChange={(e) => setField("tax_id", e.target.value)}
            required={isStepCompany}
          />
        </div>

        <div className="mb-2">
          <label className="form-label">Primary Identification Number *</label>
          <input
            name="primary_identification_number"
            className="form-control"
            value={form.fiscal_data.tax_identification.primary_identification_number}
            onKeyDown={preventEnterSubmit}
            onChange={(e) =>
              setFiscal(["tax_identification", "primary_identification_number"], e.target.value)
            }
            required={isStepCompany}
          />
        </div>

        <div className="row g-2">
          <div className="col-12 col-md-6">
            <label className="form-label">Legal Name</label>
            <input
              className="form-control"
              value={form.fiscal_data.basic_information.legal_name}
              onKeyDown={preventEnterSubmit}
              onChange={(e) => setFiscal(["basic_information", "legal_name"], e.target.value)}
            />
          </div>
          <div className="col-12 col-md-6">
            <label className="form-label">Trade Name</label>
            <input
              className="form-control"
              value={form.fiscal_data.basic_information.trade_name}
              onKeyDown={preventEnterSubmit}
              onChange={(e) => setFiscal(["basic_information", "trade_name"], e.target.value)}
            />
          </div>
        </div>

        <div className="row g-2 mt-1">
          <div className="col-12 col-md-6">
            <label className="form-label">Entity Type</label>
            <input
              className="form-control"
              value={form.fiscal_data.basic_information.entity_type}
              onKeyDown={preventEnterSubmit}
              onChange={(e) => setFiscal(["basic_information", "entity_type"], e.target.value)}
            />
          </div>
          <div className="col-12 col-md-6">
            <label className="form-label">Incorporation Date</label>
            <input
              type="date"
              className="form-control"
              value={form.fiscal_data.basic_information.incorporation_date}
              onKeyDown={preventEnterSubmit}
              onChange={(e) => setFiscal(["basic_information", "incorporation_date"], e.target.value)}
            />
          </div>
        </div>

        <div className="row g-2 mt-1">
          <div className="col-12 col-md-6">
            <label className="form-label">Incorporation Country</label>
            <input
              className="form-control"
              value={form.fiscal_data.basic_information.incorporation_country}
              onKeyDown={preventEnterSubmit}
              onChange={(e) =>
                setFiscal(["basic_information", "incorporation_country"], e.target.value)
              }
            />
          </div>
          <div className="col-12 col-md-6 form-check d-flex align-items-end ps-0">
            <input
              id="active_status"
              type="checkbox"
              className="form-check-input me-2"
              checked={form.fiscal_data.basic_information.active_status}
              onChange={(e) => setFiscal(["basic_information", "active_status"], e.target.checked)}
            />
            <label htmlFor="active_status" className="form-check-label">Active status</label>
          </div>
        </div>

        <div className="mt-3">
          <label className="form-label">Tax Address</label>
          <input
            className="form-control mb-2"
            placeholder="Address"
            value={form.fiscal_data.tax_location.tax_address.address}
            onKeyDown={preventEnterSubmit}
            onChange={(e) => setFiscal(["tax_location", "tax_address", "address"], e.target.value)}
          />
          <div className="row g-2">
            <div className="col-12 col-md-6">
              <input
                className="form-control"
                placeholder="City"
                value={form.fiscal_data.tax_location.tax_address.city}
                onKeyDown={preventEnterSubmit}
                onChange={(e) => setFiscal(["tax_location", "tax_address", "city"], e.target.value)}
              />
            </div>
            <div className="col-12 col-md-6">
              <input
                className="form-control"
                placeholder="State/Province"
                value={form.fiscal_data.tax_location.tax_address.state_province}
                onKeyDown={preventEnterSubmit}
                onChange={(e) =>
                  setFiscal(["tax_location", "tax_address", "state_province"], e.target.value)
                }
              />
            </div>
          </div>
          <div className="row g-2 mt-1">
            <div className="col-12 col-md-6">
              <input
                className="form-control"
                placeholder="Postal Code"
                value={form.fiscal_data.tax_location.tax_address.postal_code}
                onKeyDown={preventEnterSubmit}
                onChange={(e) =>
                  setFiscal(["tax_location", "tax_address", "postal_code"], e.target.value)
                }
              />
            </div>
            <div className="col-12 col-md-6">
              <input
                className="form-control"
                placeholder="Country"
                value={form.fiscal_data.tax_location.tax_address.country}
                onKeyDown={preventEnterSubmit}
                onChange={(e) => setFiscal(["tax_location", "tax_address", "country"], e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="d-flex justify-content-between mt-3">
          <button type="button" className="btn btn-secondary" onClick={back}>
            Back
          </button>
          <button type="submit" className="btn btn-primary">
            Register
          </button>
        </div>
      </section>
    ),
    [isStepCompany, form, setFiscal, setField]
  );

  const StepUserSubmit = useMemo(
    () => (
      <section aria-hidden={!isStepUserSubmit} style={{ display: isStepUserSubmit ? "block" : "none" }}>
        <h3 className="mb-3">Ready to create your account</h3>
        <div className="d-flex justify-content-between">
          <button type="button" className="btn btn-secondary" onClick={back}>
            Back
          </button>
          <button type="submit" className="btn btn-primary">
            Register
          </button>
        </div>
      </section>
    ),
    [isStepUserSubmit]
  );

  return (
    <div className="d-flex min-vh-100 align-items-center justify-content-center bg-light">
      <form
        onSubmit={handleSubmit}
        className="card shadow-card p-4 rounded-xl2 w-100"
        style={{ maxWidth: 720 }}
      >
        <h2 className="text-h1 text-center mb-3">Register</h2>

        <div className="progress mb-3" role="progressbar" aria-valuemin={0} aria-valuemax={3} aria-valuenow={activeStep}>
          <div
            className="progress-bar"
            style={{ width: `${((activeStep + 1) / 4) * 100}%` }}
          />
        </div>

        {error && <p className="text-state-danger text-center mb-3">{error}</p>}

        {StepRole}
        {StepBasic}
        {StepGuideType}
        {StepIndependent}
        {StepCompany}
        {StepUserSubmit}
      </form>
    </div>
  );
}
