import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";

const API = "http://127.0.0.1:8000/api";

export default function EditProgramModal({ program, onClose, onSaved, onDeleted }) {
  const { token } = useAuth();

  const [form, setForm] = useState({
    title: "",
    description: "",
    program_type: "", // 🔥 Ahora guardará el UUID
    min_activities: 1,
  });
  const [gallery, setGallery] = useState([]);

  // asignadas/selección
  const [assigned, setAssigned] = useState([]);
  const [selectedActivities, setSelectedActivities] = useState([]);
  const [originalIds, setOriginalIds] = useState([]);
  // búsqueda
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);

  // control
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // hidrata formulario y galería al abrir/cambiar programa
  useEffect(() => {
    if (!program) return;
    setForm({
      title: program.title || "",
      description: program.description || "",
      program_type: program.program_type || "", // 🔥 Guarda el UUID directamente
      min_activities: Number(program.min_activities) || 1,
    });
    setGallery(
      Array.isArray(program.gallery)
        ? program.gallery.map((g, i) => ({
            tag: g.tag ?? "",
            url: g.url ?? "",
            position: typeof g.position === "number" ? g.position : i,
          }))
        : []
    );
  }, [program]);

  // carga actividades ya vinculadas
  useEffect(() => {
    if (!program?.id) return;
    fetch(`${API}/programs/${program.id}/activities`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        setAssigned(data);
        const ids = data.map(a => a.id);
        setSelectedActivities(ids);
        setOriginalIds(ids); // snapshot de DB
      })
      .catch(() => {});
  }, [program?.id, token]);

  // helpers formulario/galería
  const setField = (k, v) => setForm((p) => ({ ...p, [k]: v }));
  const addGalleryItem = () =>
    setGallery((p) => [...p, { tag: "", url: "", position: p.length }]);
  const updateGalleryItem = (idx, field, value) =>
    setGallery((p) => p.map((it, i) => (i === idx ? { ...it, [field]: value } : it)));
  const removeGalleryItem = (idx) =>
    setGallery((p) => p.filter((_, i) => i !== idx).map((it, i) => ({ ...it, position: i })));

  // búsqueda
  const runSearch = async () => {
    const q = query.trim();
    if (!q) {
      setResults([]);
      return;
    }
    setSearching(true);
    try {
      const r = await fetch(`${API}/activities/search?q=${encodeURIComponent(q)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setResults(r.ok ? await r.json() : []);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  // selección
  const addOne = (a) => {
    setSelectedActivities((prev) => (prev.includes(a.id) ? prev : [...prev, a.id]));
  };
  
  const removeOne = (id) => {
    setSelectedActivities((prev) => prev.filter((x) => x !== id));
  };

  // Helper: Obtener nombre del tipo de actividad
  const getActivityTypeName = (activity) => {
    if (activity?.type?.type_name) {
      return activity.type.type_name;
    }
    return "Activity";
  };

  const handleSave = async () => {
    setSaving(true); 
    setError("");
    try {
      // 🔥 Construir payload limpio solo con campos editables
      const payload = {
        title: form.title,
        description: form.description,
        program_type: form.program_type, // UUID
        min_activities: form.min_activities,
        gallery: gallery
      };

      console.log("Updating program with payload:", payload);

      // actualiza el programa
      const res = await fetch(`${API}/programs/${program.id}`, {
        method: "PUT",
        headers: { 
          "Content-Type": "application/json", 
          Authorization: `Bearer ${token}` 
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

      const updated = await res.json();

      // diffs contra originalIds (DB en el momento de abrir)
      const toAdd = selectedActivities.filter((id) => !originalIds.includes(id));
      const toRemove = originalIds.filter((id) => !selectedActivities.includes(id));

      if (toAdd.length) {
        const rAdd = await fetch(`${API}/programs/${program.id}/activities`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify(toAdd), // array de UUIDs
        });
        if (!rAdd.ok) {
          const addError = await rAdd.text();
          throw new Error(`Error linking activities: ${addError}`);
        }
      }

      for (const id of toRemove) {
        const rDel = await fetch(`${API}/programs/${program.id}/activities/${id}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!rDel.ok) {
          throw new Error(`Error unlinking activity ${id}`);
        }
      }

      onSaved?.(updated);
      onClose();
    } catch (e) { 
      setError(e.message);
      console.error("Save error:", e);
    } finally { 
      setSaving(false); 
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    setError("");
    try {
      const res = await fetch(`${API}/programs/${program.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const t = await res.text();
        let msg = null;
        try {
          msg = JSON.parse(t).detail;
        } catch {
          msg = null;
        }
        throw new Error(msg || `Error ${res.status}`);
      }
      onDeleted?.(program.id);
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="modal d-block" tabIndex="-1" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
      <div className="modal-dialog modal-xl modal-dialog-centered">
        <div className="modal-content shadow-modal rounded-xl2">
          <div className="modal-header">
            <h2 className="text-h2 mb-0">Edit Program</h2>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>

          <div className="modal-body">
            {error && (
              <div className="alert alert-danger" style={{ whiteSpace: 'pre-wrap' }}>
                {error}
              </div>
            )}

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
            <div className="d-flex gap-2 mb-3">
              <input
                className="form-control"
                placeholder="Program Type (read-only)"
                value={program?.type?.type_name || ""}
                disabled
                readOnly
              />
              <input
                type="number"
                min={1}
                className="form-control"
                placeholder="Min activities"
                value={form.min_activities}
                onChange={(e) =>
                  setField("min_activities", Math.max(1, Number(e.target.value) || 1))
                }
              />
            </div>

            <h3 className="fw-semibold mb-2">Gallery</h3>
            {gallery.map((item, idx) => (
              <div key={idx} className="d-flex align-items-center gap-2 mb-2">
                <input
                  className="form-control w-25"
                  placeholder="Tag"
                  value={item.tag}
                  onChange={(e) => updateGalleryItem(idx, "tag", e.target.value)}
                />
                <input
                  className="form-control flex-grow-1"
                  placeholder="Image URL"
                  value={item.url}
                  onChange={(e) => updateGalleryItem(idx, "url", e.target.value)}
                />
                <input
                  type="number"
                  className="form-control w-25"
                  value={item.position}
                  onChange={(e) =>
                    updateGalleryItem(idx, "position", Number(e.target.value) || 0)
                  }
                />
                <button
                  onClick={() => removeGalleryItem(idx)}
                  className="btn btn-sm btn-danger"
                  type="button"
                >
                  ✕
                </button>
              </div>
            ))}
            <button onClick={addGalleryItem} className="btn btn-light mb-3" type="button">
              + Add Image
            </button>

            {/* Chips de asignadas */}
            <h3 className="fw-semibold mt-4 mb-2">Assigned Activities</h3>
            <div className="d-flex flex-wrap gap-2 mb-3">
              {assigned
                .filter((a) => selectedActivities.includes(a.id))
                .map((a) => (
                  <span
                    key={a.id}
                    className="badge bg-secondary-subtle text-dark d-flex align-items-center gap-2 p-2"
                  >
                    <span className="fw-semibold">{a.title}</span>
                    <span className="small">
                      {getActivityTypeName(a)} · {a.location?.display_name || "No location"}
                    </span>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-danger py-0"
                      onClick={() => removeOne(a.id)}
                    >
                      ×
                    </button>
                  </span>
                ))}
            </div>

            {/* Buscador y resultados */}
            <h3 className="fw-semibold mt-2 mb-2">Add activities</h3>
            <div className="d-flex gap-2 mb-2">
              <input
                className="form-control"
                placeholder="Search by title, type or location…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runSearch()}
              />
              <button className="btn btn-light" onClick={runSearch} disabled={searching} type="button">
                {searching ? "Searching…" : "Search"}
              </button>
            </div>

            <ul className="list-group mb-3">
              {results.map((a) => {
                const selected = selectedActivities.includes(a.id);
                return (
                  <li
                    key={a.id}
                    className="list-group-item d-flex justify-content-between align-items-center"
                  >
                    <div className="text-truncate" style={{ maxWidth: "75%" }}>
                      <div className="fw-semibold text-truncate">{a.title}</div>
                      <div className="small text-muted text-truncate">
                        {getActivityTypeName(a)} · {a.location?.display_name || "No location"}
                      </div>
                    </div>
                    {selected ? (
                      <button
                        className="btn btn-outline-danger btn-sm"
                        onClick={() => removeOne(a.id)}
                        type="button"
                      >
                        Remove
                      </button>
                    ) : (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => addOne(a)}
                        type="button"
                      >
                        Add
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>

          <div className="modal-footer">
            <button onClick={onClose} className="btn btn-secondary" type="button">
              Cancel
            </button>
            <button onClick={handleDelete} disabled={deleting} className="btn btn-outline-danger" type="button">
              {deleting ? "Deleting..." : "Delete"}
            </button>
            <button onClick={handleSave} disabled={saving} className="btn btn-primary" type="button">
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}