// frontend/src/components/AssignmentsModal.jsx
import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { api } from "../lib/api";
import { fetchScheduleAssignments, selfAssign, proposeAssignment, cancelAssignment } from "../hooks/useAssignments";

const STATUS_BADGE = {
  proposed: "bg-warning",
  accepted: "bg-success",
  rejected: "bg-danger",
  cancelled: "bg-secondary",
};

export default function AssignmentsModal({ schedule, onClose }) {
  const { user } = useAuth();
  const toast = useToast();
  const [assignments, setAssignments] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedUserId, setSelectedUserId] = useState("");
  const [proposeAsLeader, setProposeAsLeader] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [a, m] = await Promise.all([
        fetchScheduleAssignments(schedule.id),
        api.get(`/companies/${schedule.selling_company_id}/teams/${schedule.team_id}/members`),
      ]);
      setAssignments(a);
      setMembers(m);
    } catch (e) {
      setError(e.message || "Could not load staffing for this schedule");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schedule.id]);

  const myMembership = members.find((m) => m.user_id === user?.id);
  const canStaff = !!myMembership && myMembership.role_level <= 2;
  const activeLeader = assignments.find((a) => a.is_leader && (a.status === "proposed" || a.status === "accepted"));
  const assignedUserIds = new Set(
    assignments.filter((a) => a.status === "proposed" || a.status === "accepted").map((a) => a.user_id)
  );
  const availableMembers = members.filter((m) => !assignedUserIds.has(m.user_id));

  const runAction = async (fn, successMsg) => {
    setBusy(true);
    try {
      await fn();
      if (successMsg) toast.success(successMsg);
      await load();
    } catch (e) {
      toast.error(e.message || "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  const handleSelfAssign = (asLeader) =>
    runAction(() => selfAssign(schedule.id, asLeader), asLeader ? "Assigned as leader" : "Self-assigned");

  const handlePropose = () => {
    if (!selectedUserId) return;
    return runAction(
      () => proposeAssignment(schedule.id, selectedUserId, proposeAsLeader),
      "Proposal sent"
    ).then(() => {
      setSelectedUserId("");
      setProposeAsLeader(false);
    });
  };

  const handleCancel = (assignmentId) => runAction(() => cancelAssignment(assignmentId), "Cancelled");

  return (
    <div className="modal d-block" tabIndex="-1" role="dialog" style={{ background: "rgba(0,0,0,.3)" }}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Staffing — {schedule.title}</h5>
            <button className="btn-close" onClick={onClose} />
          </div>
          <div className="modal-body">
            {loading && <p className="text-muted">Loading…</p>}
            {error && <div className="alert alert-danger">{error}</div>}

            {!loading && !error && (
              <>
                <h6>Current assignments</h6>
                {assignments.length === 0 ? (
                  <p className="text-muted small">No one assigned yet.</p>
                ) : (
                  <ul className="list-group mb-3">
                    {assignments.map((a) => (
                      <li key={a.id} className="list-group-item d-flex justify-content-between align-items-center">
                        <div>
                          {a.user_display_name}
                          {a.is_leader ? " · Leader" : ""}{" "}
                          <span className={`badge ${STATUS_BADGE[a.status] || "bg-secondary"}`}>{a.status}</span>
                        </div>
                        {canStaff && (a.status === "proposed" || a.status === "accepted") && (
                          <button
                            className="btn btn-sm btn-outline-secondary"
                            disabled={busy}
                            onClick={() => handleCancel(a.id)}
                          >
                            Cancel
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                )}

                {canStaff ? (
                  <div className="border-top pt-3">
                    <h6>Staff this schedule</h6>
                    <div className="d-flex flex-wrap gap-2 mb-3">
                      <button
                        className="btn btn-sm btn-outline-primary"
                        disabled={busy || assignedUserIds.has(user.id)}
                        onClick={() => handleSelfAssign(false)}
                      >
                        Self-assign
                      </button>
                      <button
                        className="btn btn-sm btn-outline-primary"
                        disabled={busy || assignedUserIds.has(user.id) || !!activeLeader}
                        onClick={() => handleSelfAssign(true)}
                        title={activeLeader ? "This schedule already has a leader" : undefined}
                      >
                        Self-assign as leader
                      </button>
                    </div>

                    <div className="row g-2 align-items-end">
                      <div className="col-12 col-md-6">
                        <label className="form-label small">Propose a teammate</label>
                        <select
                          className="form-select"
                          value={selectedUserId}
                          onChange={(e) => setSelectedUserId(e.target.value)}
                        >
                          <option value="">Select a guide…</option>
                          {availableMembers.map((m) => (
                            <option key={m.user_id} value={m.user_id}>
                              {m.user_name || m.user_email} (level {m.role_level})
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="col-6 col-md-3 d-flex align-items-center">
                        <div className="form-check">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id="proposeAsLeader"
                            checked={proposeAsLeader}
                            disabled={!!activeLeader}
                            onChange={(e) => setProposeAsLeader(e.target.checked)}
                          />
                          <label className="form-check-label small" htmlFor="proposeAsLeader">
                            As leader
                          </label>
                        </div>
                      </div>
                      <div className="col-6 col-md-3">
                        <button
                          className="btn btn-primary w-100"
                          disabled={busy || !selectedUserId}
                          onClick={handlePropose}
                        >
                          Propose
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-muted small mb-0">
                    Only this team's leadership can staff a schedule.
                  </p>
                )}
              </>
            )}
          </div>
          <div className="modal-footer">
            <button className="btn btn-light" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
