// frontend/src/pages/MembershipRequests.jsx
import { useState } from "react";
import { useMembershipRequests } from "../hooks/useMembershipRequests";
import { useToast } from "../context/ToastContext";

const STATUS_BADGE = {
  pending: "bg-warning",
  accepted: "bg-success",
  rejected: "bg-danger",
  cancelled: "bg-secondary",
  expired: "bg-secondary",
};

function RequestRow({ req, children }) {
  return (
    <li className="list-group-item d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center gap-2">
      <div>
        <div className="fw-semibold">
          {req.direction === "invitation" ? "Invitation" : "Application"} · {req.team_name || "Team"}
          {" "}
          <span className={`badge ${STATUS_BADGE[req.status] || "bg-secondary"}`}>{req.status}</span>
        </div>
        <div className="small text-muted">
          {req.company_name} · offered level {req.offered_level}
          {req.target_display_name ? ` · for ${req.target_display_name}` : ""}
        </div>
        {req.message && <div className="small fst-italic mt-1">"{req.message}"</div>}
        {req.target_consent === "pending" && (
          <div className="small text-warning-emphasis mt-1">Waiting on the proposed guide's consent</div>
        )}
      </div>
      <div className="d-flex gap-2">{children}</div>
    </li>
  );
}

export default function MembershipRequests() {
  const {
    incoming,
    outgoing,
    teamPending,
    departure,
    loading,
    error,
    invite,
    apply,
    consent,
    accept,
    reject,
    cancel,
    leaveTeam,
  } = useMembershipRequests();
  const toast = useToast();

  const [applyTeamId, setApplyTeamId] = useState("");
  const [applyMessage, setApplyMessage] = useState("");
  const [applying, setApplying] = useState(false);
  const [leaving, setLeaving] = useState(false);

  const runAction = async (fn, successMsg) => {
    try {
      await fn();
      if (successMsg) toast.success(successMsg);
    } catch (e) {
      toast.error(e.message || "Something went wrong");
    }
  };

  const handleApply = async (e) => {
    e.preventDefault();
    if (!applyTeamId.trim()) return;
    setApplying(true);
    try {
      await apply({ teamId: applyTeamId.trim(), message: applyMessage.trim() || undefined });
      toast.success("Application sent");
      setApplyTeamId("");
      setApplyMessage("");
    } catch (e) {
      toast.error(e.message || "Could not send application");
    } finally {
      setApplying(false);
    }
  };

  const handleLeave = async () => {
    if (!window.confirm("Leave your current team?")) return;
    setLeaving(true);
    try {
      await leaveTeam();
      toast.success("You have left your team");
    } catch (e) {
      toast.error(e.message || "Could not leave team");
    } finally {
      setLeaving(false);
    }
  };

  return (
    <div className="container py-4">
      <h2 className="text-h2 mb-3">Team Membership</h2>
      {error && <div className="alert alert-danger">{error}</div>}
      {loading && <p className="text-muted">Loading…</p>}

      <div className="card shadow-card mb-4">
        <div className="card-body">
          <h5 className="card-title">Leave your team</h5>
          {departure.can_leave ? (
            <p className="text-muted mb-2">You're free to leave your current team at any time.</p>
          ) : (
            <div className="alert alert-warning mb-2">{departure.reason}</div>
          )}
          <button
            className="btn btn-outline-danger"
            disabled={!departure.can_leave || leaving}
            onClick={handleLeave}
          >
            {leaving ? "Leaving…" : "Leave team"}
          </button>
        </div>
      </div>

      <div className="card shadow-card mb-4">
        <div className="card-body">
          <h5 className="card-title">Apply to a team</h5>
          <p className="text-muted small">
            Ask the team you want to join for their team ID, then apply below.
          </p>
          <form className="row g-2 align-items-end" onSubmit={handleApply}>
            <div className="col-12 col-md-5">
              <label className="form-label small">Team ID</label>
              <input
                className="form-control"
                value={applyTeamId}
                onChange={(e) => setApplyTeamId(e.target.value)}
                placeholder="Team UUID"
              />
            </div>
            <div className="col-12 col-md-5">
              <label className="form-label small">Message (optional)</label>
              <input
                className="form-control"
                value={applyMessage}
                onChange={(e) => setApplyMessage(e.target.value)}
                placeholder="Why you'd like to join"
              />
            </div>
            <div className="col-12 col-md-2">
              <button className="btn btn-primary w-100" disabled={applying || !applyTeamId.trim()}>
                {applying ? "Sending…" : "Apply"}
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="card shadow-card mb-4">
        <div className="card-body">
          <h5 className="card-title">Incoming</h5>
          {incoming.length === 0 ? (
            <p className="text-muted mb-0">Nothing needs your attention right now.</p>
          ) : (
            <ul className="list-group">
              {incoming.map((req) => (
                <RequestRow key={req.id} req={req}>
                  {req.target_consent === "pending" ? (
                    <>
                      <button
                        className="btn btn-sm btn-success"
                        onClick={() => runAction(() => consent(req.id, "granted"), "Consent granted")}
                      >
                        Grant consent
                      </button>
                      <button
                        className="btn btn-sm btn-outline-danger"
                        onClick={() => runAction(() => consent(req.id, "refused"), "Consent refused")}
                      >
                        Refuse
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        className="btn btn-sm btn-success"
                        onClick={() => runAction(() => accept(req.id), "Accepted")}
                      >
                        Accept
                      </button>
                      <button
                        className="btn btn-sm btn-outline-danger"
                        onClick={() => runAction(() => reject(req.id), "Declined")}
                      >
                        Decline
                      </button>
                    </>
                  )}
                </RequestRow>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="card shadow-card mb-4">
        <div className="card-body">
          <h5 className="card-title">Requests for teams you manage</h5>
          {teamPending.length === 0 ? (
            <p className="text-muted mb-0">No pending requests for your teams.</p>
          ) : (
            <ul className="list-group">
              {teamPending.map((req) => (
                <RequestRow key={req.id} req={req}>
                  <button
                    className="btn btn-sm btn-success"
                    disabled={req.target_consent === "pending"}
                    onClick={() => runAction(() => accept(req.id), "Accepted")}
                    title={req.target_consent === "pending" ? "Waiting on the guide's consent first" : undefined}
                  >
                    Accept
                  </button>
                  <button
                    className="btn btn-sm btn-outline-danger"
                    onClick={() => runAction(() => reject(req.id), "Rejected")}
                  >
                    Reject
                  </button>
                </RequestRow>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="card shadow-card">
        <div className="card-body">
          <h5 className="card-title">Sent by you</h5>
          {outgoing.length === 0 ? (
            <p className="text-muted mb-0">You haven't sent any invitations or applications.</p>
          ) : (
            <ul className="list-group">
              {outgoing.map((req) => (
                <RequestRow key={req.id} req={req}>
                  {req.status === "pending" && (
                    <button
                      className="btn btn-sm btn-outline-secondary"
                      onClick={() => runAction(() => cancel(req.id), "Cancelled")}
                    >
                      Cancel
                    </button>
                  )}
                </RequestRow>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
