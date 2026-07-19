import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, apiFetch, ApiError, getAuth, setAuth as persistAuth, clearAuth } from "../lib/api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [access, setAccess] = useState(null);
  const [refresh, setRefresh] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const saved = getAuth();
    if (saved?.access) {
      setAccess(saved.access);
      setRefresh(saved.refresh || null);
      setUser(saved.user || null);
    }
    setLoading(false);

    // Fired by lib/api.js when a background token refresh fails.
    const onAuthLogout = () => {
      setAccess(null);
      setRefresh(null);
      setUser(null);
    };
    window.addEventListener("auth:logout", onAuthLogout);
    return () => window.removeEventListener("auth:logout", onAuthLogout);
  }, []);

  const persist = (payload) => {
    persistAuth(payload);
    if (payload.access !== undefined) setAccess(payload.access);
    if (payload.refresh !== undefined) setRefresh(payload.refresh);
    if (payload.user !== undefined) setUser(payload.user);
  };

  const fetchMe = async () => {
    try {
      return await api.get("/users/me");
    } catch {
      return null;
    }
  };

  const login = async (email, password) => {
    let data;
    try {
      data = await api.post("/auth/login", { email, password }, { skipAuth: true });
    } catch (err) {
      throw new Error(err instanceof ApiError ? err.message : `Login failed`);
    }
    // {access_token, refresh_token, token_type, user}
    persist({ access: data.access_token, refresh: data.refresh_token, user: data.user });

    let merged = data.user;
    const me = await fetchMe();
    if (me) {
      merged = { ...(data.user || {}), ...me };
      persist({ user: merged });
    }
    return merged;
  };

  const refreshMe = async () => {
    if (!access) return null;
    const me = await fetchMe();
    if (me) persist({ user: { ...(user || {}), ...me } });
    return me;
  };

  const logout = () => {
    setAccess(null);
    setRefresh(null);
    setUser(null);
    clearAuth();
  };

  // Legacy wrapper kept for existing callers passing a full URL + init.
  // Refresh-and-retry-once-on-401 now lives in lib/api.js's apiFetch.
  const fetchWithAuth = async (input, init = {}) => apiFetch(input, init);

  // Password recovery
  const requestPasswordReset = async (email) => {
    try {
      return await api.post("/auth/request-password-reset", { email }, { skipAuth: true });
    } catch {
      throw new Error("No se pudo solicitar recuperación");
    }
  };

  const resetPassword = async (token, new_password) => {
    try {
      return await api.post("/auth/reset-password", { token, new_password }, { skipAuth: true });
    } catch {
      throw new Error("No se pudo resetear la contraseña");
    }
  };

  const value = useMemo(
    () => ({
      token: access,
      refresh,
      user,
      loading,
      login,
      logout,
      refreshMe,
      fetchWithAuth,
      requestPasswordReset,
      resetPassword,
    }),
    [access, refresh, user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
