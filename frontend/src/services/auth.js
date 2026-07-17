// frontend/src/services/auth.js
/*export const apiLogin = async (email, password) => {
  const response = await fetch("http://127.0.0.1:8000/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw await response.json();
  return response.json();
};*/
// frontend/src/services/auth.js
const API = (import.meta.env.VITE_API ?? "http://127.0.0.1:8000/api").replace(/\/+$/, "");

export const apiLogin = async (email, password) => {
  const response = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw await response.json();
  return response.json();
};
