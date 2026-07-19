import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import SearchableSelect from "../components/SearchableSelect";

const API = import.meta.env.VITE_API || "http://127.0.0.1:8000/api";

export default function CreateProgram() {
  const { token } = useAuth();
  const [step, setStep] = useState(1);

  const [form, setForm] = useState({
    title: "",
    description: "",
    program_type: "",
    min_activities: 1,
    is_shared: false,
  });
  const [gallery, setGallery] = useState([]);
  const [error, setError] = useState("");

  // States para tipos
  const [types, setTypes] = useState([]);
  const [loadingTypes, setLoadingTypes] = useState(false);
  const [typesError, setTypesError] = useState("");

  const setField = (k, v) => setForm((p) => ({ ...p, [k]: v }));

  // Cargar tipos para programas
  useEffect(() => {
    const fetchTypes = async () => {
      setLoadingTypes(true);
      setTypesError("");
      try {
        const res = await fetch(`${API}/types/?experience_type=program`);
        
        if (!res.ok) {
          const errorText = await res.text();
          console.error("Types API error:", errorText);
          throw new Error(`API returned ${res.status}: ${errorText}`);
        }
        
        const data = await res.json();
        console.log("Program types loaded:", data);
        
        if (!Array.isArray(data)) {
          throw new Error("API did not return an array");
        }
        
        setTypes(data);
        
        if (data.length > 0) {
          setForm(prev => ({ ...prev, program_type: data[0].id }));
        } else {
          setTypesError("No program types found in database");
        }
      } catch (err) {
        console.error("Error loading types:", err);
        setTypesError(err.message || "Failed to load types");
        setTypes([]);
      } finally {
        setLoadingTypes(false);
      }
    };

    fetchTypes();
  }, []);

  const typeOptions = Array.isArray(types) ? types.map(t => ({
    value: t.id,
    label: t.type_name,
    badge: t.experience_type === "both" ? "both" : undefined
  })) : [];

  const addGalleryItem = () =>
    setGallery((prev) => [
      ...prev,
      { tag: "", url: "", position: prev.length },
    ]);

  const updateGalleryItem = (idx, field, value) =>
    setGallery((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, [field]: value } : item))
    );

  const removeGalleryItem = (idx) =>
    setGallery((prev) =>
      prev
        .filter((_, i) => i !== idx)
        .map((item, i) => ({ ...item, position: i }))
    );

  const handleSubmit = async () => {
    setError("");
    if (!token) {
      setError("Session not valid. Login.");
      return;
    }

    if (!form.program_type) {
      setError("Debes seleccionar un tipo de programa.");
      return;
    }

    try {
      const payload = { ...form, gallery };
      console.log("Sending payload:", payload);
      
      const res = await fetch(`${API}/programs/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const contentType = res.headers.get("content-type");
        let errorMessage = `Error ${res.status}`;
        
        if (contentType && contentType.includes("application/json")) {
          const j = await res.json();
          console.error("Error response:", j);
          errorMessage = j.detail || JSON.stringify(j);
        } else {
          const text = await res.text();
          console.error("Error response (text):", text);
          errorMessage = text || errorMessage;
        }
        
        throw new Error(errorMessage);
      }

      const created = await res.json();
      console.log("Program created:", created);
      alert("Program created successfully!");
      
      // Reset form
      setForm({
        title: "",
        description: "",
        program_type: types.length > 0 ? types[0].id : "",
        min_activities: 1,
        is_shared: false,
      });
      setGallery([]);
      setStep(1);
    } catch (e) {
      const errorMsg = e.message || String(e);
      setError(errorMsg);
      console.error("Submit error:", e);
    }
  };

  return (
    <div className="container my-4">
      <div className="card shadow-card rounded-xl2">
        <div className="card-body">
          <h2 className="text-h2 mb-4">Create Program</h2>
          {error && <div className="alert alert-danger">{error}</div>}

          {step === 1 && (
            <>
              <input
                className="form-control mb-3"
                placeholder="Title"
                value={form.title}
                onChange={(e) => setField("title", e.target.value)}
              />
              <textarea
                className="form-control mb-3"
                placeholder="Description"
                value={form.description}
                onChange={(e) => setField("description", e.target.value)}
              />
              <button
                className="btn btn-primary"
                onClick={() => setStep(2)}
                disabled={!form.title.trim()}
              >
                Next
              </button>
            </>
          )}

          {step === 2 && (
            <>
              <div className="mb-3">
                <label className="form-label fw-semibold">Program Type *</label>
                {loadingTypes ? (
                  <div className="text-muted">Loading types...</div>
                ) : typesError ? (
                  <div className="alert alert-warning">
                    <strong>Error loading types:</strong> {typesError}
                    <br />
                    <small>Check console for details or contact admin.</small>
                  </div>
                ) : types.length === 0 ? (
                  <div className="alert alert-danger">
                    No program types available. Please contact admin to add types in the database.
                  </div>
                ) : (
                  <SearchableSelect
                    options={typeOptions}
                    value={form.program_type}
                    onChange={(val) => setField("program_type", val)}
                    placeholder="Select program type..."
                    loading={loadingTypes}
                  />
                )}
              </div>

              <div className="mb-3">
                <label className="form-label fw-semibold">Minimum Activities</label>
                <input
                  type="number"
                  className="form-control"
                  placeholder="Min activities"
                  min="1"
                  value={form.min_activities}
                  onChange={(e) =>
                    setField("min_activities", Number(e.target.value) || 1)
                  }
                />
              </div>

              <div className="d-flex gap-2">
                <button
                  className="btn btn-secondary"
                  onClick={() => setStep(1)}
                >
                  Back
                </button>
                <button
                  className="btn btn-primary"
                  onClick={() => setStep(3)}
                  disabled={!form.program_type}
                >
                  Next
                </button>
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <h3 className="fw-semibold mb-3">Gallery (Optional)</h3>
              <p className="text-muted small mb-3">Add images for your program. You can skip this step.</p>

              {gallery.map((item, idx) => (
                <div key={idx} className="d-flex align-items-center gap-2 mb-2">
                  <input
                    type="text"
                    placeholder="Tag"
                    className="form-control"
                    style={{ maxWidth: 150 }}
                    value={item.tag}
                    onChange={(e) =>
                      updateGalleryItem(idx, "tag", e.target.value)
                    }
                  />
                  <input
                    type="text"
                    placeholder="Image URL"
                    className="form-control flex-grow-1"
                    value={item.url}
                    onChange={(e) =>
                      updateGalleryItem(idx, "url", e.target.value)
                    }
                  />
                  <input
                    type="number"
                    className="form-control"
                    style={{ maxWidth: 80 }}
                    placeholder="Order"
                    value={item.position}
                    onChange={(e) =>
                      updateGalleryItem(idx, "position", Number(e.target.value))
                    }
                  />
                  <button
                    onClick={() => removeGalleryItem(idx)}
                    className="btn btn-sm btn-danger"
                  >
                    ✕
                  </button>
                </div>
              ))}

              <button
                onClick={addGalleryItem}
                className="btn btn-outline-primary mb-4"
              >
                + Add Image
              </button>

              <div className="form-check mb-4">
                <input
                  type="checkbox"
                  className="form-check-input"
                  id="programIsShared"
                  checked={form.is_shared}
                  onChange={(e) => setField("is_shared", e.target.checked)}
                />
                <label className="form-check-label" htmlFor="programIsShared">
                  Allow teams in other companies to schedule this program
                </label>
              </div>

              <div className="d-flex gap-2">
                <button
                  className="btn btn-secondary"
                  onClick={() => setStep(2)}
                >
                  Back
                </button>
                <button
                  className="btn btn-success"
                  onClick={handleSubmit}
                >
                  Create Program
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}