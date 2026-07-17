import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";

export default function EditActivityModal({ activity, onClose, onSaved, onDeleted }) {
  const { token } = useAuth();
  const [form, setForm] = useState({
    title: activity?.title || "",
    description: activity?.description || "",
    activity_type: activity?.activity_type || "exploration",
    location_id: activity?.location_id || null,
  });
  const [gallery, setGallery] = useState(activity?.gallery || []);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
    useEffect(() => {
    if (!activity) return;
    setForm({
      title: activity.title ?? "",
      description: activity.description ?? "",
      activity_type: activity.type?.type_name ?? "exploration",
      location_id: activity.location_id ?? null,
    });
    setGallery(Array.isArray(activity.gallery) ? activity.gallery : []);
  }, [activity]);
  const setField = (k, v) => setForm((p) => ({ ...p, [k]: v }));
  const addGalleryItem = () => setGallery((p) => [...p, { tag: "", url: "", position: p.length }]);
  const updateGalleryItem = (idx, field, value) =>
    setGallery((p) => p.map((it, i) => (i === idx ? { ...it, [field]: value } : it)));
  const removeGalleryItem = (idx) =>
    setGallery((p) => p.filter((_, i) => i !== idx).map((it, i) => ({ ...it, position: i })));

  const handleSave = async () => {
    setSaving(true); setError("");
    try {
      const payload = { ...form, gallery };
      const res = await fetch(`http://127.0.0.1:8000/api/activities/${activity.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || "Error updating activity");
      }
      const updated = await res.json();
      onSaved?.(updated);
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true); setError("");
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/activities/${activity.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const text = await res.text();
  console.error("DELETE failed:", res.status, text);
  const msg = (() => { try { return JSON.parse(text).detail } catch { return null } })();
  throw new Error(msg || "Error deleting activity")
      }
      onDeleted?.(activity.id);
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="modal d-block" tabIndex="-1" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
      <div className="modal-dialog modal-lg modal-dialog-centered">
        <div className="modal-content shadow-modal rounded-xl2">
          <div className="modal-header">
            <h2 className="text-h2 mb-0">Edit Activity</h2>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>
          <div className="modal-body">
            {error && <p className="text-state-danger">{error}</p>}

            <input className="form-control mb-3" placeholder="Title"
              value={form.title} onChange={(e) => setField("title", e.target.value)} />
            <textarea className="form-control mb-3" placeholder="Description"
              value={form.description} onChange={(e) => setField("description", e.target.value)} />
            <input className="form-control mb-3" placeholder="Type"
              value={form.activity_type} onChange={(e) => setField("activity_type", e.target.value)} />

            <h3 className="fw-semibold mb-2">Gallery</h3>
            {gallery.map((item, idx) => (
              <div key={idx} className="d-flex align-items-center gap-2 mb-2">
                <input className="form-control w-25" placeholder="Tag"
                  value={item.tag} onChange={(e) => updateGalleryItem(idx, "tag", e.target.value)} />
                <input className="form-control flex-grow-1" placeholder="Image URL"
                  value={item.url} onChange={(e) => updateGalleryItem(idx, "url", e.target.value)} />
                <input type="number" className="form-control w-25"
                  value={item.position}
                  onChange={(e) => updateGalleryItem(idx, "position", Number(e.target.value))} />
                <button onClick={() => removeGalleryItem(idx)} className="btn btn-sm btn-danger">✕</button>
              </div>
            ))}
            <button onClick={addGalleryItem} className="btn btn-light mb-3">+ Add Image</button>
          </div>
          <div className="modal-footer">
            <button onClick={onClose} className="btn btn-secondary">Cancel</button>
            <button onClick={handleDelete} disabled={deleting} className="btn btn-outline-danger">
              {deleting ? "Deleting..." : "Delete"}
            </button>
            <button onClick={handleSave} disabled={saving} className="btn btn-primary">
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
