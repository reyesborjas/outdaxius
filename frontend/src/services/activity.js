// Named exports exactly as imported in CreateActivity.jsx
// services/activity.js
/*export async function searchLocations(query) {
  const res = await fetch(
    `http://127.0.0.1:8000/api/locations/search?q=${encodeURIComponent(query)}`
  );
  if (res.status === 404) return []; // no results
  if (!res.ok) throw await res.json();
  return res.json(); // [{ id, display_name, ... }]
}

export async function createActivity(payload, token) {
  if (!token) throw { detail: "Missing auth token" };
  const res = await fetch("http://127.0.0.1:8000/api/activities", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${String(token).trim()}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}*/
// services/activity.js
const API = (import.meta.env.VITE_API ?? "http://127.0.0.1:8000/api").replace(/\/+$/, "");

export async function searchLocations(query) {
  const res = await fetch(`${API}/locations/search?q=${encodeURIComponent(query)}`);
  if (res.status === 404) return [];
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function createActivity(payload, token) {
  if (!token) throw { detail: "Missing auth token" };
  const res = await fetch(`${API}/activities`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${String(token).trim()}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}
