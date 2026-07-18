import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import SearchableSelect from "../components/SearchableSelect";

const API = import.meta.env.VITE_API || "http://127.0.0.1:8000/api";

async function searchLocations(query) {
  const res = await fetch(`${API}/locations/search?q=${encodeURIComponent(query)}`);
  if (res.status === 404) return [];
  if (!res.ok) throw await res.json();
  return res.json();
}

async function createLocation(payload) {
  const res = await fetch(`${API}/locations/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export default function CreateActivity() {
  const { token } = useAuth();
  const [step, setStep] = useState(1);
  const [guides, setGuides] = useState([]);
  const [loadingGuides, setLoadingGuides] = useState(false);
  const [form, setForm] = useState({
    title: "",
    description: "",
    activity_type: "",
    location_id: null,
    guide_leader: null,
  });
  const [gallery, setGallery] = useState([]);
  const [error, setError] = useState("");

  const [types, setTypes] = useState([]);
  const [loadingTypes, setLoadingTypes] = useState(false);
  const [typesError, setTypesError] = useState("");

  const [locationQuery, setLocationQuery] = useState("");
  const [locationResults, setLocationResults] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [searching, setSearching] = useState(false);

  const [plusCode, setPlusCode] = useState("");
  const [gmapsUrl, setGmapsUrl] = useState("");
  const [lat, setLat] = useState(0);
  const [lon, setLon] = useState(0);

  const setField = (k, v) => setForm((p) => ({ ...p, [k]: v }));

  // Cargar tipos filtrados por 'activity' o 'both'
  useEffect(() => {
    const fetchTypes = async () => {
      setLoadingTypes(true);
      setTypesError("");
      try {
        const res = await fetch(`${API}/types/?experience_type=activity`);
        
        console.log("Types API response status:", res.status);
        
        if (!res.ok) {
          const errorText = await res.text();
          console.error("Types API error:", errorText);
          throw new Error(`API returned ${res.status}: ${errorText}`);
        }
        
        const data = await res.json();
        console.log("Types loaded:", data);
        
        if (!Array.isArray(data)) {
          throw new Error("API did not return an array");
        }
        
        setTypes(data);
        
        if (data.length > 0) {
          setForm(prev => ({ ...prev, activity_type: data[0].id }));
        } else {
          setTypesError("No activity types found in database");
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

useEffect(() => {
  const fetchGuides = async () => {
    if (!token) {
      console.log("No token available, skipping guides fetch");
      return;
    }
    
    setLoadingGuides(true);
    try {
      const res = await fetch(`${API}/users?role=guide`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!res.ok) {
        console.error("Failed to load guides:", res.status);
        setGuides([]);
        return;
      }
      
      const data = await res.json();
      console.log("Guides loaded:", data);
      setGuides(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Error loading guides:", err);
      setGuides([]);
    } finally {
      setLoadingGuides(false);
    }
  };

  fetchGuides();
}, [token]);

// Preparar opciones para guide_leader
const guideOptions = guides.map(g => ({
  value: g.id,
  label: g.display_name || g.email
}));

  const typeOptions = Array.isArray(types) ? types.map(t => ({
    value: t.id,
    label: t.type_name,
    badge: t.experience_type === "both" ? "both" : undefined
  })) : [];

  const addGalleryItem = () =>
    setGallery((prev) => [...prev, { tag: "", url: "", position: prev.length }]);
  const updateGalleryItem = (idx, field, value) =>
    setGallery((prev) => prev.map((it, i) => (i === idx ? { ...it, [field]: value } : it)));
  const removeGalleryItem = (idx) =>
    setGallery((prev) => prev.filter((_, i) => i !== idx).map((it, i) => ({ ...it, position: i })));

  const handleSearchLocation = async () => {
    setSearching(true);
    try {
      const results = await searchLocations(locationQuery.trim());
      setLocationResults(results);
    } catch {
      setLocationResults([]);
    } finally {
      setSearching(false);
    }
  };

  const validGmaps = (u) =>
    /^https?:\/\//i.test(u) && /(google\.com\/maps|goo\.gl\/maps|maps\.app\.goo\.gl)/i.test(u);

  const handleCreateLocation = async () => {
    setError("");
    const name = locationQuery.trim();
    if (!name) return setError("Ingresa un nombre de ubicación.");
    if (!plusCode.trim()) return setError("Ingresa el plus_code.");
    if (!gmapsUrl.trim()) return setError("Ingresa la Google Maps URL.");
    if (!validGmaps(gmapsUrl.trim())) return setError("URL de Google Maps inválida.");

    try {
      const newLoc = await createLocation({
        display_name: name,
        lat: Number(lat) || 0,
        lon: Number(lon) || 0,
        plus_code: plusCode.trim(),
        google_maps_url: gmapsUrl.trim(),
      });
      setSelectedLocation(newLoc);
      setField("location_id", newLoc.id);
      setLocationResults([]);
    } catch (e) {
      setError(e?.detail || "Error creando la ubicación.");
    }
  };

  const handleSubmit = async () => {
    setError("");

    if (!token) {
      setError("Sesión no válida. Inicia sesión.");
      return;
    }

    if (!form.activity_type) {
      setError("Debes seleccionar un tipo de actividad.");
      return;
    }

    if (!form.location_id) {
      setError("Debes seleccionar una ubicación.");
      return;
    }

    try {
      const payload = { 
        title: form.title,
        description: form.description,
        activity_type: form.activity_type,
        location_id: form.location_id,
        gallery: gallery
      };

      console.log("Sending payload:", payload);

      const res = await fetch(`${API}/activities/`, {
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
          
          // Manejar errores de validación de Pydantic
          if (Array.isArray(j.detail)) {
            errorMessage = j.detail.map(err => {
              const field = Array.isArray(err.loc) ? err.loc.join('.') : 'unknown';
              return `${field}: ${err.msg}`;
            }).join('\n');
          } else if (typeof j.detail === 'string') {
            errorMessage = j.detail;
          } else {
            errorMessage = JSON.stringify(j.detail);
          }
        } else {
          const text = await res.text();
          console.error("Error response (text):", text);
          errorMessage = text || errorMessage;
        }
        
        throw new Error(errorMessage);
      }

      const created = await res.json();
      console.log("Activity created:", created);
      alert("Activity created successfully!");
      
      // Reset form
      setForm({
        title: "",
        description: "",
        activity_type: types.length > 0 ? types[0].id : "",
        location_id: null,
      });
      setGallery([]);
      setStep(1);
      setSelectedLocation(null);
      setLocationQuery("");
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
          <h2 className="text-h2 mb-4">Create Activity</h2>
          {error && (
            <div className="alert alert-danger" style={{ whiteSpace: 'pre-wrap' }}>
              {error}
            </div>
          )}

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
                rows={4}
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
                <label className="form-label fw-semibold">Activity Type *</label>
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
                    No activity types available. Please contact admin to add types in the database.
                  </div>
                ) : (
                  <SearchableSelect
                    options={typeOptions}
                    value={form.activity_type}
                    onChange={(val) => setField("activity_type", val)}
                    placeholder="Select activity type..."
                    loading={loadingTypes}
                  />
                )}
              </div>
              <div className="mb-3">
                <label className="form-label fw-semibold">Location *</label>
                     <input
                       className="form-control mb-2"
                       placeholder="Search location by name"
                       value={locationQuery}
                       onChange={(e) => setLocationQuery(e.target.value)}
                       onKeyDown={(e) => e.key === 'Enter' && handleSearchLocation()}
                          />
                          <button 
                            type="button" 
                            className="btn btn-outline-secondary w-100 mb-3" 
                            onClick={handleSearchLocation}
                            disabled={searching || !locationQuery.trim()}
                          >
                            {searching ? "Searching..." : "Search Location"}
                          </button>
                        </div>
                <div className="mb-3">
                <label className="form-label fw-semibold">Guide Leader (Optional)</label>
                <p className="small text-muted">Defaults to you if not selected</p>
                {loadingGuides ? (
                  <div className="text-muted">Loading guides...</div>
                ) : guides.length === 0 ? (
                  <div className="alert alert-info">No guides available</div>
                ) : (
                  <SearchableSelect
                    options={guideOptions}
                    value={form.guide_leader}
                    onChange={(val) => setField("guide_leader", val)}
                    placeholder="Select guide leader..."
                    loading={loadingGuides}
                  />
                )}
              </div>

              <div className="d-flex gap-2 mt-4">
                {/* ... botones existentes ... */}
              </div>
              {locationResults.length > 0 && (
                <ul className="list-group mb-3">
                  {locationResults.map((loc) => (
                    <li
                      key={loc.id}
                      className={`list-group-item list-group-item-action ${selectedLocation?.id === loc.id ? 'active' : ''}`}
                      onClick={() => {
                        setSelectedLocation(loc);
                        setField("location_id", loc.id);
                      }}
                      style={{ cursor: 'pointer' }}
                    >
                      <strong>{loc.display_name}</strong>
                      {loc.google_maps_url && (
                        <a 
                          href={loc.google_maps_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="ms-2 small"
                          onClick={(e) => e.stopPropagation()}
                        >
                          (maps)
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              )}

              {selectedLocation && (
                <div className="alert alert-success">
                  ✓ Selected: <strong>{selectedLocation.display_name}</strong>
                </div>
              )}

              {locationResults.length === 0 && locationQuery.trim() && !searching && (
                <div className="border rounded p-3 bg-light mb-3">
                  <h6 className="mb-3">Create new location</h6>
                  <div className="row g-2">
                    <div className="col-md-6">
                      <label className="form-label small">Plus code *</label>
                      <input
                        className="form-control form-control-sm"
                        value={plusCode}
                        onChange={(e) => setPlusCode(e.target.value)}
                        placeholder="e.g., 8G2P+4C Santiago"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label small">Google Maps URL *</label>
                      <input
                        className="form-control form-control-sm"
                        value={gmapsUrl}
                        onChange={(e) => setGmapsUrl(e.target.value)}
                        placeholder="https://maps.google.com/..."
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label small">Latitude (optional)</label>
                      <input
                        type="number"
                        className="form-control form-control-sm"
                        value={lat}
                        onChange={(e) => setLat(e.target.value)}
                        step="any"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label small">Longitude (optional)</label>
                      <input
                        type="number"
                        className="form-control form-control-sm"
                        value={lon}
                        onChange={(e) => setLon(e.target.value)}
                        step="any"
                      />
                    </div>
                  </div>
                  <button 
                    type="button" 
                    className="btn btn-warning btn-sm mt-3" 
                    onClick={handleCreateLocation}
                  >
                    Create Location
                  </button>
                </div>
              )}

              <div className="d-flex gap-2 mt-4">
                <button className="btn btn-secondary" onClick={() => setStep(1)}>
                  Back
                </button>
                <button
                  className="btn btn-primary"
                  onClick={() => setStep(3)}
                  disabled={!form.location_id || !form.activity_type}
                >
                  Next
                </button>
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <h3 className="fw-semibold mb-3">Gallery (Optional)</h3>
              <p className="text-muted small mb-3">Add images for your activity. You can skip this step.</p>
              
              {gallery.map((item, idx) => (
                <div key={idx} className="d-flex align-items-center gap-2 mb-2">
                  <input
                    type="text"
                    placeholder="Tag"
                    className="form-control"
                    style={{ maxWidth: 150 }}
                    value={item.tag}
                    onChange={(e) => updateGalleryItem(idx, "tag", e.target.value)}
                  />
                  <input
                    type="text"
                    placeholder="Image URL"
                    className="form-control flex-grow-1"
                    value={item.url}
                    onChange={(e) => updateGalleryItem(idx, "url", e.target.value)}
                  />
                  <input
                    type="number"
                    className="form-control"
                    style={{ maxWidth: 80 }}
                    placeholder="Order"
                    value={item.position}
                    onChange={(e) => updateGalleryItem(idx, "position", Number(e.target.value))}
                  />
                  <button 
                    onClick={() => removeGalleryItem(idx)} 
                    className="btn btn-sm btn-danger"
                  >
                    ✕
                  </button>
                </div>
              ))}

              <button onClick={addGalleryItem} className="btn btn-outline-primary mb-4">
                + Add Image
              </button>

              <div className="d-flex gap-2">
                <button className="btn btn-secondary" onClick={() => setStep(2)}>
                  Back
                </button>
                <button className="btn btn-success" onClick={handleSubmit}>
                  Create Activity
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}