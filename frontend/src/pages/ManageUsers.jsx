import React, { useEffect, useState, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

// Helper para normalizar roles
function normalizeRole(role) {
  switch (role) {
    case "admin":
      return "Admin";
    case "guide":
      return "Guide";
    case "user":
      return "User";
    default:
      return role;
  }
}

// CORRECCIÓN: Función para construir URLs completas
const buildBackendUrl = (endpoint) => {
  const baseUrl = (import.meta.env.VITE_API || "http://127.0.0.1:8000/api").replace(/\/$/, "");
  return `${baseUrl}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
};

export default function ManageUsers() {
  const { user, fetchWithAuth } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState();
  const [refreshing, setRefreshing] = useState(false);

  // Verificar permisos - sólo admin y guide pueden acceder
  useEffect(() => {
    if (!user) return;
    if (user.role !== "admin" && user.role !== "guide") {
      navigate("/main");
    }
  }, [user, navigate]);

  // Función para cargar usuarios - CORREGIDA con URLs completas
  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      // CORRECCIÓN: Construir URL completa manualmente
      let endpoint = "/users";
      if (q.trim().length > 0) {
        endpoint += `?search=${encodeURIComponent(q.trim())}`;
      }
      
      const fullUrl = buildBackendUrl(endpoint);
      console.log("Fetching users from:", fullUrl);
      
      const res = await fetchWithAuth(fullUrl, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      });
      
      console.log("Response status:", res.status, res.statusText);
      
      if (!res.ok) {
        const errorText = await res.text();
        console.error("Error response:", errorText);
        throw new Error(`Error fetching users: ${res.status} ${res.statusText}`);
      }
      
      const items = await res.json();
      console.log("Users received:", items);
      setUsers(Array.isArray(items) ? items : []);
    } catch (e) {
      setError(String(e.message || e));
      console.error("Error fetching users:", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [fetchWithAuth, q]);

  // Cargar usuarios cuando el componente se monta o cambian las dependencias
  useEffect(() => {
    if (user && (user.role === "admin" || user.role === "guide")) {
      fetchUsers();
    }
  }, [user, fetchUsers]);

  // Manejar activación/desactivación de usuarios
  const handleToggleActive = async (userId, currentActive) => {
    if (!window.confirm(`Are you sure you want to ${currentActive ? "deactivate" : "activate"} this user?`)) return;
    
    try {
      setRefreshing(true);
      // CORRECCIÓN: URL completa para PATCH
      const fullUrl = buildBackendUrl(`/users/${userId}`);
      const res = await fetchWithAuth(
        fullUrl,
        {
          method: "PATCH",
          headers: { 
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ is_active: !currentActive }),
        }
      );
      
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Failed to update user status: ${res.status} ${errorText}`);
      }
      
      // Recargar la lista de usuarios
      await fetchUsers();
    } catch (e) {
      setError(String(e.message || e));
      setRefreshing(false);
    }
  };

  // Manejar asignación de roles
  const handleAssignRole = async (userId, newRole) => {
    if (!window.confirm(`Are you sure you want to assign role "${newRole}" to this user?`)) return;
    
    try {
      setRefreshing(true);
      
      // CORRECCIÓN: Construir URL completa
      const fullUrl = buildBackendUrl(`/roles/assign?userid=${userId}&role=${newRole}`);
      console.log("Assigning role:", fullUrl);
      
      const res = await fetchWithAuth(fullUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Failed to assign role: ${res.status} ${errorText}`);
      }
      
      // Recargar la lista de usuarios
      await fetchUsers();
    } catch (e) {
      alert(`Error asignando rol: ${e.message}`);
      setError(String(e.message || e));
      setRefreshing(false);
    }
  };

  return (
    <div className="container py-4">
      <h2 className="text-h2 mb-3">Manage Users</h2>
      <p className="mb-3">
        {user?.role === "admin" 
          ? "Admins can view, search, modify roles, and activate/deactivate all users (except other admins)." 
          : "Guides can view and search all users."}
      </p>
      
      {/* Barra de búsqueda */}
      <div className="mb-4 d-flex gap-2 flex-wrap align-items-center">
        <input
          type="text"
          className="form-control"
          placeholder="Search by name, email..."
          value={q}
          onChange={e => setQ(e.target.value)}
          onKeyDown={e => e.key === "Enter" && fetchUsers()}
          style={{ maxWidth: 340 }}
        />
        <button 
          className="btn btn-outline-primary" 
          onClick={fetchUsers} 
          disabled={loading || refreshing}
        >
          {loading || refreshing ? (
            <>
              <span className="spinner-border spinner-border-sm me-2" role="status"></span>
              Searching...
            </>
          ) : (
            "Search"
          )}
        </button>
        <button 
          className="btn btn-outline-secondary" 
          onClick={() => {
            setQ("");
            setTimeout(() => fetchUsers(), 100);
          }}
          disabled={loading || refreshing}
        >
          Clear
        </button>
      </div>
      
      {/* Mensajes de error */}
      {error && (
        <div className="alert alert-danger d-flex align-items-center" role="alert">
          <i className="bi bi-exclamation-triangle-fill me-2"></i>
          <div style={{ whiteSpace: 'pre-wrap' }}>{error}</div>
        </div>
      )}
      
      {/* Estado de carga */}
      {loading && (
        <div className="text-center py-4">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading users...</span>
          </div>
          <p className="text-muted mt-2">Loading users...</p>
        </div>
      )}
      
      {/* Sin resultados */}
      {!loading && users.length === 0 && !error && (
        <div className="text-center py-4">
          <p className="text-muted">No users found.</p>
          {q && <p className="text-muted">Try adjusting your search terms.</p>}
        </div>
      )}
      
      {/* Tabla de usuarios */}
      {!loading && users.length > 0 && (
        <div className="table-responsive">
          <table className="table table-striped align-middle">
            <thead className="table-light">
              <tr>
                <th>Display Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>First / Last Name</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td>
                    <strong>{u.display_name || u.displayname || "-"}</strong>
                  </td>
                  <td>{u.email}</td>
                  <td>
                    <span className={`badge ${
                      u.role === "admin" ? "bg-danger" : 
                      u.role === "guide" ? "bg-warning" : "bg-secondary"
                    }`}>
                      {normalizeRole(u.role)}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${u.is_active ? "bg-success" : "bg-danger"}`}>
                      {u.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td>
                    {u.first_name || u.firstname || "-"} {u.last_name || u.lastname || "-"}
                  </td>
                  <td>
                    {/* Solo los admins pueden modificar roles y activar/desactivar */}
                    {user?.role === "admin" && u.role !== "admin" && (
                      <div className="d-flex flex-column gap-2">
                        {/* Selector de rol */}
                        <select
                          className="form-select form-select-sm"
                          value={u.role}
                          onChange={(e) => handleAssignRole(u.id, e.target.value)}
                          disabled={refreshing}
                          title="Change user role"
                        >
                          <option value="user">User</option>
                          <option value="guide">Guide</option>
                          <option value="admin">Admin</option>
                        </select>
                        
                        {/* Botón activar/desactivar */}
                        <button
                          className={`btn btn-sm ${u.is_active ? "btn-outline-warning" : "btn-outline-success"}`}
                          onClick={() => handleToggleActive(u.id, u.is_active)}
                          disabled={refreshing}
                          title={u.is_active ? "Deactivate user" : "Activate user"}
                        >
                          {refreshing ? (
                            <span className="spinner-border spinner-border-sm" role="status"></span>
                          ) : u.is_active ? (
                            "Deactivate"
                          ) : (
                            "Activate"
                          )}
                        </button>
                      </div>
                    )}
                    
                    {user?.role === "guide" && (
                      <span className="text-muted">View only</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}