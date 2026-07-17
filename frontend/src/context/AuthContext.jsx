import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";

const API = (import.meta.env.VITE_API ?? "http://127.0.0.1:8000/api").replace(/\/$/, "");
const join = (p) => `${API}${p.startsWith("/") ? "" : "/"}${p}`;

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [access, setAccess] = useState(null);
  const [refresh, setRefresh] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const refreshing = useRef(null); // promesa en curso

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("auth") || "null");
      if (saved?.access) {
        setAccess(saved.access);
        setRefresh(saved.refresh || null);
        setUser(saved.user || null);
      }
    } catch {}
    setLoading(false);
  }, []);

  const persist = (payload) => {
    const v = { access: payload.access ?? access, refresh: payload.refresh ?? refresh, user: payload.user ?? user };
    localStorage.setItem("auth", JSON.stringify(v));
    if (payload.access !== undefined) setAccess(payload.access);
    if (payload.refresh !== undefined) setRefresh(payload.refresh);
    if (payload.user !== undefined) setUser(payload.user);
  };

  const fetchMe = async (tkn) => {
    const res = await fetch(join("/users/me"), { headers: { Authorization: `Bearer ${tkn}`, Accept: "application/json" } });
    if (!res.ok) return null;
    return res.json();
  };

  const login = async (email, password) => {
    const res = await fetch(join("/auth/login"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      let detail = txt; try { detail = JSON.parse(txt).detail; } catch {}
      throw new Error(detail || `Login failed ${res.status}`);
    }
    const data = await res.json(); // {access_token, refresh_token, token_type, user}
    persist({ access: data.access_token, refresh: data.refresh_token, user: data.user });

    let merged = data.user;
    try {
      const me = await fetchMe(data.access_token);
      if (me) {
        merged = { ...(data.user || {}), ...me };
        persist({ user: merged });
      }
    } catch {}
    return merged;
  };

  const refreshOnce = async () => {
    if (!refresh) return null;
    if (!refreshing.current) {
      refreshing.current = (async () => {
        const r = await fetch(join("/auth/refresh"), {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!r.ok) {
          logout();
          refreshing.current = null;
          return null;
        }
        const d = await r.json(); // {access_token, refresh_token}
        persist({ access: d.access_token, refresh: d.refresh_token });
        refreshing.current = null;
        return d.access_token;
      })();
    }
    return refreshing.current;
  };

  // Wrapper que renueva y reintenta 401 una sola vez
  const fetchWithAuth = async (input, init = {}) => {
    const res = await fetch(input, {
      ...init,
      headers: { ...(init.headers || {}), Authorization: access ? `Bearer ${access}` : undefined },
    });
    if (res.status !== 401) return res;
    const newAccess = await refreshOnce();
    if (!newAccess) return res;
    return fetch(input, {
      ...init,
      headers: { ...(init.headers || {}), Authorization: `Bearer ${newAccess}` },
    });
  };

  const refreshMe = async () => {
    if (!access) return null;
    const me = await fetchMe(access);
    if (me) persist({ user: { ...(user || {}), ...me } });
    return me;
  };

  const logout = () => {
    setAccess(null); setRefresh(null); setUser(null);
    localStorage.removeItem("auth");
  };

  // Password recovery
  const requestPasswordReset = async (email) => {
    const r = await fetch(join("/auth/request-password-reset"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ email }),
    });
    if (!r.ok) throw new Error("No se pudo solicitar recuperación");
    return r.json();
  };

  const resetPassword = async (token, new_password) => {
    const r = await fetch(join("/auth/reset-password"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ token, new_password }),
    });
    if (!r.ok) throw new Error("No se pudo resetear la contraseña");
    return r.json();
  };

  const value = useMemo(
    () => ({ 
      token: access, refresh, user, loading, login, logout, refreshMe, fetchWithAuth, requestPasswordReset, resetPassword }),
    [access, refresh, user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
