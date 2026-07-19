// frontend/src/lib/api.js
export const API = (import.meta.env.VITE_API ?? "http://127.0.0.1:8000/api").replace(/\/+$/, "");

function join(path) {
  if (/^https?:\/\//i.test(path)) return path; // already-absolute URL (legacy callers)
  return `${API}${path.startsWith("/") ? "" : "/"}${path}`;
}

function getAuth() {
  try {
    return JSON.parse(localStorage.getItem("auth") || "null");
  } catch {
    return null;
  }
}

function setAuth(patch) {
  const current = getAuth() || {};
  const next = { ...current, ...patch };
  localStorage.setItem("auth", JSON.stringify(next));
  return next;
}

function clearAuth() {
  localStorage.removeItem("auth");
}

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

let refreshPromise = null;

// Single-flight refresh: concurrent 401s share one in-flight refresh call.
async function refreshAccessToken() {
  const auth = getAuth();
  if (!auth?.refresh) return null;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(join("/auth/refresh"), {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ refresh_token: auth.refresh }),
        });
        if (!res.ok) {
          clearAuth();
          window.dispatchEvent(new Event("auth:logout"));
          return null;
        }
        const data = await res.json(); // {access_token, refresh_token}
        setAuth({ access: data.access_token, refresh: data.refresh_token });
        return data.access_token;
      } catch {
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

/**
 * Low-level fetch wrapper: joins the base URL, attaches the auth header,
 * attaches X-Company-Id (from options.companyId or the active company in
 * localStorage), and retries once on 401 after a token refresh.
 *
 * Returns the raw Response — use apiJson/api.* for parsed+throwing calls.
 */
export async function apiFetch(path, options = {}) {
  const { companyId, skipAuth, headers: extraHeaders, ...rest } = options;
  const activeCompanyId = companyId ?? localStorage.getItem("activeCompanyId");

  const buildHeaders = (token) => {
    const h = { Accept: "application/json", ...extraHeaders };
    if (rest.body && !(rest.body instanceof FormData) && h["Content-Type"] === undefined) {
      h["Content-Type"] = "application/json";
    }
    if (!skipAuth && token) h.Authorization = `Bearer ${token}`;
    if (activeCompanyId) h["X-Company-Id"] = activeCompanyId;
    return h;
  };

  const auth = getAuth();
  let res = await fetch(join(path), { ...rest, headers: buildHeaders(auth?.access) });

  if (res.status === 401 && !skipAuth && auth?.refresh) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      res = await fetch(join(path), { ...rest, headers: buildHeaders(newAccess) });
    }
  }

  return res;
}

async function parseBody(res) {
  const text = await res.text().catch(() => "");
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/**
 * Calls apiFetch, parses the JSON body, and throws ApiError on non-2xx.
 */
export async function apiJson(path, options = {}) {
  const res = await apiFetch(path, options);
  const data = await parseBody(res);
  if (!res.ok) {
    const detail =
      (data && typeof data === "object" && (data.detail || data.message)) ||
      (typeof data === "string" && data) ||
      `Error ${res.status}`;
    throw new ApiError(typeof detail === "string" ? detail : `Error ${res.status}`, res.status, data);
  }
  return data;
}

function withBody(method) {
  return (path, body, options = {}) =>
    apiJson(path, {
      ...options,
      method,
      body: body === undefined || body === null ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    });
}

export const api = {
  get: (path, options = {}) => apiJson(path, { ...options, method: "GET" }),
  post: withBody("POST"),
  put: withBody("PUT"),
  patch: withBody("PATCH"),
  delete: (path, options = {}) => apiJson(path, { ...options, method: "DELETE" }),
};

export { getAuth, setAuth, clearAuth, join as joinApiUrl };
