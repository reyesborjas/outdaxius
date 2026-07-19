import React, { useEffect, useState, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";

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

export default function ManageUsers() {
  const { user } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState();
  const [refreshing, setRefreshing] = useState(false);
  const [isCompanyAdmin, setIsCompanyAdmin] = useState(false);

  // Verificar permisos - sólo admin y guide pueden acceder
  useEffect(() => {
    if (!user) return;
    if (user.role !== "admin" && user.role !== "guide") {
      navigate("/main");
    }
  }, [user, navigate]);

  // Company admins (commercial axis, company_members.is_admin) can also manage their own
  // company's members here, alongside platform admins.
  useEffect(() => {
    if (!user || user.role === "admin") return;
    api
      .get("/users/me/company-info")
      .then((info) => setIsCompanyAdmin(!!(info?.type === "company_member" && info?.is_admin)))
      .catch(() => setIsCompanyAdmin(false));
  }, [user]);

  const canManage = user?.role === "admin" || isCompanyAdmin;

  // Función para cargar usuarios - CORREGIDA con URLs completas
  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      let endpoint = "/users";
      if (q.trim().length > 0) {
        endpoint += `?search=${encodeURIComponent(q.trim())}`;
      }

      const items = await api.get(endpoint);
      setUsers(Array.isArray(items) ? items : []);
    } catch (e) {
      setError(String(e.message || e));
      console.error("Error fetching users:", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [q]);

  // Cargar usuarios cuando el componente se monta o cambian las dependencias
  useEffect(() => {
    if (user && (user.role === "admin" || user.role === "guide")) {
      fetchUsers();
    }
  }, [user, fetchUsers]);

  // Platform admins: activate/deactivate the user's platform account (users.is_active).
  const handleToggleActive = async (userId, currentActive) => {
    if (!window.confirm(`Are you sure you want to ${currentActive ? "deactivate" : "activate"} this user?`)) return;

    try {
      setRefreshing(true);
      await api.patch(`/users/${userId}`, { is_active: !currentActive });

      // Recargar la lista de usuarios
      await fetchUsers();
    } catch (e) {
      setError(String(e.message || e));
      setRefreshing(false);
    }
  };

  // Company admins: remove the person from THIS company (company_members.is_active) -- does not
  // touch their platform account. They stop appearing in this company-scoped list once removed.
  // PUT /companymembers/{id} requires position (no default), so it must be resent unchanged;
  // is_admin is resent too so removal doesn't silently reset a fellow admin's commercial role.
  const handleRemoveFromCompany = async (targetUser) => {
    if (!window.confirm("Remove this person from the company? They can be re-invited later.")) return;

    try {
      setRefreshing(true);
      await api.put(`/companymembers/${targetUser.company_member_id}`, {
        position: targetUser.company_position,
        is_admin: !!targetUser.is_company_admin,
        is_active: false,
      });

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
      await api.post(`/roles/assign?userid=${userId}&role=${newRole}`);

      // Recargar la lista de usuarios
      await fetchUsers();
    } catch (e) {
      toast.error(`Error asignando rol: ${e.message}`);
      setError(String(e.message || e));
      setRefreshing(false);
    }
  };

  return (
    <div className="container py-4">
      <h2 className="text-h2 mb-3">Manage Users</h2>
      <p className="mb-3">
        {user?.role === "admin"
          ? "Platform admins can view, search, modify roles, and activate/deactivate every user."
          : isCompanyAdmin
          ? "Showing yourself and your company's members. As a company admin, you can remove members from the company."
          : "Showing yourself and your company's members."}
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
                    {/* Platform admins: full control over role + platform account status. */}
                    {user?.role === "admin" && u.role !== "admin" && (
                      <div className="d-flex flex-column gap-2">
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

                    {/* Company admins: remove company-mates from the company. Never touches
                        platform role or platform account status -- see handleRemoveFromCompany. */}
                    {user?.role !== "admin" && isCompanyAdmin && u.id !== user?.id && u.company_member_id && (
                      <button
                        className="btn btn-sm btn-outline-danger"
                        onClick={() => handleRemoveFromCompany(u)}
                        disabled={refreshing}
                        title="Remove from company"
                      >
                        {refreshing ? (
                          <span className="spinner-border spinner-border-sm" role="status"></span>
                        ) : (
                          "Remove from company"
                        )}
                      </button>
                    )}

                    {!canManage && (
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