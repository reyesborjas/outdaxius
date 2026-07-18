// frontend/src/pages/CompanyDashboard.jsx
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCompany } from "../hooks/useCompany";
import InviteGuideModal from "../components/InviteGuideModal";

const API = import.meta.env.VITE_API || "http://127.0.0.1:8000/api";

// Cascading hierarchy, lower number = more power (see app/core/permissions.py).
const ROLE_LEVEL_LABELS = { 1: "Master guide", 2: "Planner", 3: "Coordinator", 4: "Field guide" };

export default function CompanyDashboard() {
  const { companyId } = useParams();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const {
    company,
    license,
    members,
    invitations,
    loading,
    error,
    createInvitation,
    removeMember,
  } = useCompany(companyId);

  const [showInviteModal, setShowInviteModal] = useState(false);
  const [actionError, setActionError] = useState("");
  
  // Teams state
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [teamMembers, setTeamMembers] = useState([]);
  const [newTeamName, setNewTeamName] = useState("");
  const [newTeamDescription, setNewTeamDescription] = useState("");
  const [teamsError, setTeamsError] = useState("");
  const [creatingTeam, setCreatingTeam] = useState(false);
  const [loadingTeamMembers, setLoadingTeamMembers] = useState(false);
  
  // Add member modal
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);
  const [selectedMemberToAdd, setSelectedMemberToAdd] = useState("");

  const isAdmin = members.some(
    (m) => m.userid === user?.id && m.is_admin && m.is_active
  );

  // Load teams
  useEffect(() => {
    if (!companyId || !token) return;
    fetch(`${API}/companies/${companyId}/teams`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Error ${r.status}`);
        return r.json();
      })
      .then(setTeams)
      .catch((err) => {
        console.error("Error loading teams:", err);
        setTeams([]);
      });
  }, [companyId, token, creatingTeam]);

  // Load team members when team is selected
  useEffect(() => {
    if (!selectedTeam || !token) return;
    
    setLoadingTeamMembers(true);
    fetch(`${API}/companies/${companyId}/teams/${selectedTeam.id}/members`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Error ${r.status}`);
        return r.json();
      })
      .then(setTeamMembers)
      .catch((err) => {
        console.error("Error loading team members:", err);
        setTeamMembers([]);
      })
      .finally(() => setLoadingTeamMembers(false));
  }, [selectedTeam, companyId, token]);

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    setTeamsError("");
    if (!newTeamName.trim()) {
      setTeamsError("Team name is required");
      return;
    }
    setCreatingTeam(true);
    try {
      const res = await fetch(`${API}/companies/${companyId}/teams`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ 
          name: newTeamName,
          description: newTeamDescription || null
        }),
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Could not create team");
      }
      
      const newTeam = await res.json();
      setTeams(prev => [...prev, newTeam]);
      setNewTeamName("");
      setNewTeamDescription("");
    } catch (e) {
      setTeamsError(e.message);
    } finally {
      setCreatingTeam(false);
    }
  };

  const handleAddMember = async () => {
    if (!selectedMemberToAdd) return;
    
    try {
      const res = await fetch(
        `${API}/companies/${companyId}/teams/${selectedTeam.id}/members`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ user_id: selectedMemberToAdd }),
        }
      );
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Could not add member");
      }
      
      // Reload team members
      const membersRes = await fetch(
        `${API}/companies/${companyId}/teams/${selectedTeam.id}/members`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (membersRes.ok) {
        const updatedMembers = await membersRes.json();
        setTeamMembers(updatedMembers);
      }
      
      setShowAddMemberModal(false);
      setSelectedMemberToAdd("");
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleRemoveMember = async (memberId) => {
    if (!window.confirm("Remove this member from the team?")) return;
    
    try {
      const res = await fetch(
        `${API}/companies/${companyId}/teams/${selectedTeam.id}/members/${memberId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Could not remove member");
      }
      
      // Update local state
      setTeamMembers(prev => prev.filter(m => m.id !== memberId));
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleRoleChange = async (memberId, newRoleLevel) => {
    const roleLevel = Number(newRoleLevel);
    try {
      const res = await fetch(
        `${API}/companies/${companyId}/teams/${selectedTeam.id}/members/${memberId}/role`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ role_level: roleLevel }),
        }
      );

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Could not update role");
      }

      // Update local state
      setTeamMembers(prev =>
        prev.map(m => (m.id === memberId ? { ...m, role_level: roleLevel } : m))
      );
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleInvite = async (email, expiresInDays) => {
    try {
      await createInvitation(email, expiresInDays);
      setShowInviteModal(false);
      setActionError("");
    } catch (err) {
      throw err;
    }
  };

  const handleRemoveCompanyMember = async (userId) => {
    if (!window.confirm("Are you sure you want to remove this member?")) return;
    try {
      await removeMember(userId);
      setActionError("");
    } catch (err) {
      setActionError(err.message);
    }
  };

  // Available guides for adding to team (must hold the guide role, be active,
  // and not already be in the selected team)
  const availableGuides = members.filter(
    m => m.is_active &&
    m.user_role === "guide" &&
    !teamMembers.some(tm => tm.user_id === m.userid)
  );

  if (loading) {
    return (
      <div className="container py-4">
        <div className="text-center">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container py-4">
        <div className="alert alert-danger">{error}</div>
      </div>
    );
  }

  useEffect(() => {
  if (companyId) localStorage.setItem("activeCompanyId", companyId);
}, [companyId]);

const [limitsData, setLimitsData] = useState(null);

useEffect(() => {
  if (!companyId || !token) return;
  fetch(`${API}/companies/${companyId}/limits`, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then(r => r.ok ? r.json() : Promise.reject(r))
    .then(setLimitsData)
    .catch(() => setLimitsData(null));
}, [companyId, token]);

  return (
    <div className="container py-4">
      {/* Company Header */}
      <div className="card shadow-card mb-4">
        <div className="card-body">
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <h2 className="text-h2 mb-2">{company?.name}</h2>
              <p className="text-muted mb-0">{company?.description}</p>
            </div>
            {isAdmin && (
              <button
                className="btn btn-outline-primary"
                onClick={() => navigate(`/main/${user.email}/company/${companyId}/edit`)}
              >
                Edit Company
              </button>
            )}
          </div>

          {/* License Info */}
          {license && (
            <div className="mt-3 p-3 bg-light rounded">
              <h6 className="fw-semibold mb-2">License Information</h6>
              <div className="row g-3">
                <div className="col-md-3">
                  <div className="small text-muted">Tier</div>
                  <div className="fw-semibold text-capitalize">{license.tier}</div>
                </div>
                <div className="col-md-3">
                  <div className="small text-muted">Guides</div>
                  <div className="fw-semibold">
                    {license.current_guides} / {license.max_guides || '∞'}
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="small text-muted">Status</div>
                  <div className={`badge ${license.can_add_guides ? 'bg-success' : 'bg-warning'}`}>
                    {license.can_add_guides ? 'Can Add Guides' : 'Limit Reached'}
                  </div>
                </div>
                {license.expires_at && (
                  <div className="col-md-3">
                    <div className="small text-muted">Expires</div>
                    <div className="fw-semibold">
                      {new Date(license.expires_at).toLocaleDateString()}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      {limitsData && (
            <div className="card shadow-card mb-4">
              <div className="card-header">
                <h5 className="mb-0">Freeware Limits (Tier: {limitsData.tier})</h5>
              </div>
              <div className="card-body">
                <div className="table-responsive">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Metric</th>
                        <th>Usage</th>
                        <th>Limit</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Guides</td>
                        <td>{license?.current_guides ?? "-"}</td>
                        <td>{limitsData.limits.guides_max ?? "∞"}</td>
                      </tr>
                      <tr>
                        <td>Total activities (historical)</td>
                        <td>{limitsData.usage_historical.activities}</td>
                        <td>{limitsData.limits.max_activities ?? "∞"}</td>
                      </tr>
                      <tr>
                        <td>Total programs (historical)</td>
                        <td>{limitsData.usage_historical.programs}</td>
                        <td>{limitsData.limits.max_programs ?? "∞"}</td>
                      </tr>
                      <tr>
                        <td>Total schedules (historical)</td>
                        <td>{limitsData.usage_historical.schedules_total}</td>
                        <td>{limitsData.limits.max_schedules_total ?? "∞"}</td>
                      </tr>
                      <tr>
                        <td>Monthly bookings (current month)</td>
                        <td>{limitsData.usage_current_month.bookings}</td>
                        <td>{limitsData.limits.max_monthly_bookings ?? "∞"}</td>
                      </tr>
                      <tr>
                        <td>Monthly participants (current month)</td>
                        <td>{limitsData.usage_current_month.participants}</td>
                        <td>{limitsData.limits.max_monthly_participants ?? "∞"}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <small className="text-muted">Historical usage includes ex-members (no is_active filter).</small>
              </div>
            </div>
          )}

      {actionError && (
        <div className="alert alert-danger alert-dismissible">
          {actionError}
          <button type="button" className="btn-close" onClick={() => setActionError("")}></button>
        </div>
      )}

      {/* Teams Section */}
      <div className="card shadow-card mb-4">
        <div className="card-body">
          <h4 className="mb-3">Teams</h4>
          
          {isAdmin && (
            <form onSubmit={handleCreateTeam} className="mb-3">
              <div className="row g-2">
                <div className="col-md-4">
                  <input
                    className="form-control"
                    value={newTeamName}
                    onChange={e => setNewTeamName(e.target.value)}
                    placeholder="Team name *"
                    disabled={creatingTeam}
                  />
                </div>
                <div className="col-md-5">
                  <input
                    className="form-control"
                    value={newTeamDescription}
                    onChange={e => setNewTeamDescription(e.target.value)}
                    placeholder="Description (optional)"
                    disabled={creatingTeam}
                  />
                </div>
                <div className="col-md-3">
                  <button type="submit" className="btn btn-primary w-100" disabled={creatingTeam}>
                    {creatingTeam ? "Creating..." : "Create Team"}
                  </button>
                </div>
              </div>
              {teamsError && <div className="alert alert-danger mt-2 mb-0">{teamsError}</div>}
            </form>
          )}

          <div className="row">
            {/* Teams List */}
            <div className="col-md-4">
              <div className="list-group">
                {teams.length === 0 && (
                  <div className="list-group-item">No teams created yet</div>
                )}
                {teams.map(team => (
                  <button
                    key={team.id}
                    type="button"
                    className={`list-group-item list-group-item-action ${
                      selectedTeam?.id === team.id ? 'active' : ''
                    }`}
                    onClick={() => setSelectedTeam(team)}
                  >
                    <div className="d-flex justify-content-between align-items-center">
                      <div>
                        <strong>{team.name}</strong>
                        {team.description && (
                          <div className="small text-muted">{team.description}</div>
                        )}
                      </div>
                      <span className="badge bg-secondary">{team.member_count || 0}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Team Members */}
            <div className="col-md-8">
              {selectedTeam ? (
                <>
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <h5 className="mb-0">Members of {selectedTeam.name}</h5>
                    {isAdmin && (
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => setShowAddMemberModal(true)}
                        disabled={availableGuides.length === 0}
                      >
                        + Add Member
                      </button>
                    )}
                  </div>

                  {loadingTeamMembers ? (
                    <div className="text-center py-4">
                      <div className="spinner-border spinner-border-sm" role="status"></div>
                    </div>
                  ) : teamMembers.length === 0 ? (
                    <p className="text-muted">No members in this team yet</p>
                  ) : (
                    <div className="table-responsive">
                      <table className="table table-hover">
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Role</th>
                            {isAdmin && <th>Actions</th>}
                          </tr>
                        </thead>
                        <tbody>
                          {teamMembers.map(member => (
                            <tr key={member.id}>
                              <td>{member.user_name || '-'}</td>
                              <td>{member.user_email}</td>
                              <td>
                                {isAdmin ? (
                                  <select
                                    className="form-select form-select-sm"
                                    value={member.role_level}
                                    onChange={(e) => handleRoleChange(member.id, e.target.value)}
>
<option value={1}>{ROLE_LEVEL_LABELS[1]}</option>
<option value={2}>{ROLE_LEVEL_LABELS[2]}</option>
<option value={3}>{ROLE_LEVEL_LABELS[3]}</option>
<option value={4}>{ROLE_LEVEL_LABELS[4]}</option>
</select>
) : (
<span className="badge bg-secondary">{ROLE_LEVEL_LABELS[member.role_level] || member.role_level}</span>
)}
</td>
{isAdmin && (
<td>
<button
className="btn btn-sm btn-outline-danger"
onClick={() => handleRemoveMember(member.id)}
>
Remove
</button>
</td>
)}
</tr>
))}
</tbody>
</table>
</div>
)}
</>
) : (
<div className="text-center text-muted py-5">
Select a team to view members
</div>
)}
</div>
</div>
</div>
</div>
  {/* Company Members */}
  <div className="card shadow-card mb-4">
    <div className="card-header d-flex justify-content-between align-items-center">
      <h5 className="mb-0">Company Members ({members.length})</h5>
      {isAdmin && license?.can_add_guides && (
        <button className="btn btn-primary btn-sm" onClick={() => setShowInviteModal(true)}>
          + Invite Guide
        </button>
      )}
    </div>
    <div className="card-body">
      <div className="table-responsive">
        <table className="table table-hover">
          <thead>
            <tr>
              <th>User</th>
              <th>Position</th>
              <th>Admin</th>
              {isAdmin && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.userid}>
                <td>{m.user_display_name || m.user_full_name || m.user?.display_name}</td>
                <td>{m.position}</td>
                <td>
                  {m.is_admin ? (
                    <span className="badge bg-primary">Admin</span>
                  ) : (
                    <span className="badge bg-secondary">Member</span>
                  )}
                </td>
                {isAdmin && (
                  <td>
                    {m.userid !== user?.id && (
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleRemoveCompanyMember(m.userid)}
                      >
                        Remove
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  {/* Pending Invitations */}
  {isAdmin && invitations.length > 0 && (
    <div className="card shadow-card">
      <div className="card-header">
        <h5 className="mb-0">Pending Invitations</h5>
      </div>
      <div className="card-body">
        <div className="table-responsive">
          <table className="table table-hover">
            <thead>
              <tr>
                <th>Email</th>
                <th>Status</th>
                <th>Created</th>
                <th>Expires</th>
              </tr>
            </thead>
            <tbody>
              {invitations
                .filter((inv) => inv.status === 'pending')
                .map((inv) => (
                  <tr key={inv.id}>
                    <td>{inv.invited_email}</td>
                    <td><span className="badge bg-warning">Pending</span></td>
                    <td>{new Date(inv.created_at).toLocaleDateString()}</td>
                    <td>{new Date(inv.expires_at).toLocaleDateString()}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )}

  {/* Invite Modal */}
  {showInviteModal && (
    <InviteGuideModal
      companyId={companyId}
      onClose={() => setShowInviteModal(false)}
      onSuccess={() => {
        setShowInviteModal(false);
        window.location.reload();
      }}
    />
  )}

{/* Add Member Modal */}
{showAddMemberModal && (
  <div className="modal show d-block" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
    <div className="modal-dialog">
      <div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title">Add Member to {selectedTeam.name}</h5>
          <button className="btn-close" onClick={() => setShowAddMemberModal(false)}></button>
        </div>
        <div className="modal-body">
          <select
            className="form-select"
            value={selectedMemberToAdd}
            onChange={(e) => setSelectedMemberToAdd(e.target.value)}
          >
            <option value="">Select a guide...</option>
            {availableGuides.map(guide => (
              <option key={guide.userid} value={guide.userid}>
                {/* 🔥 CAMBIO: Mostrar display_name en el dropdown */}
                {guide.user_display_name || 
                 guide.user_full_name || 
                 guide.user?.display_name || 
                 guide.user_email || 
                 guide.user?.email || 
                 guide.userid}
              </option>
            ))}
          </select>
          {availableGuides.length === 0 && (
            <div className="alert alert-info mt-2">
              All company guides are already in this team
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={() => setShowAddMemberModal(false)}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleAddMember}
            disabled={!selectedMemberToAdd}
          >
            Add Member
          </button>
        </div>
      </div>
    </div>
  </div>
)}
</div>
);
}
