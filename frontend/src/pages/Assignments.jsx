// frontend/src/pages/Assignments.jsx
import { useState } from "react";
import { useAssignments } from "../hooks/useAssignments";
import { useToast } from "../context/ToastContext";

const STATUS_BADGE = {
  proposed: "bg-warning",
  accepted: "bg-success",
  rejected: "bg-danger",
  cancelled: "bg-secondary",
};

function fmt(dt) {
  return dt ? new Date(dt).toLocaleString() : "-";
}

function AssignmentRow({ a, children }) {
  return (
    <li className="list-group-item d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center gap-2">
      <div>
        <div className="fw-semibold">
          {a.activity_title || "Activity"}
          {a.is_leader ? " · Leader" : ""}
          {" "}
          <span className={`badge ${STATUS_BADGE[a.status] || "bg-secondary"}`}>{a.status}</span>
        </div>
        <div className="small text-muted">
          {fmt(a.schedule_start)} – {fmt(a.schedule_end)}
        </div>
        {a.status !== "proposed" && (
          <div className="small text-muted">Proposed by {a.user_display_name || a.proposed_by}</div>
        )}
        {a.decline_reason && <div className="small fst-italic mt-1">Declined: "{a.decline_reason}"</div>}
      </div>
      <div className="d-flex gap-2">{children}</div>
    </li>
  );
}

export default function Assignments() {
  const { incoming, mine, loading, error, respond, cancel } = useAssignments();
  const toast = useToast();
  const [declining, setDeclining] = useState(null);
  const [declineReason, setDeclineReason] = useState("");

  const runAction = async (fn, successMsg) => {
    try {
      await fn();
      if (successMsg) toast.success(successMsg);
    } catch (e) {
      toast.error(e.message || "Something went wrong");
    }
  };

  const submitDecline = async () => {
    if (!declining) return;
    await runAction(() => respond(declining, "decline", declineReason.trim() || undefined), "Declined");
    setDeclining(null);
    setDeclineReason("");
  };

  const history = mine.filter((a) => a.status !== "proposed");

  return (
    <div className="container py-4">
      <h2 className="text-h2 mb-3">My Assignments</h2>
      {error && <div className="alert alert-danger">{error}</div>}
      {loading && <p className="text-muted">Loading…</p>}

      <div className="card shadow-card mb-4">
        <div className="card-body">
          <h5 className="card-title">Awaiting your response</h5>
          {incoming.length === 0 ? (
            <p className="text-muted mb-0">Nothing needs your attention right now.</p>
          ) : (
            <ul className="list-group">
              {incoming.map((a) => (
                <AssignmentRow key={a.id} a={a}>
                  <button
                    className="btn btn-sm btn-success"
                    onClick={() => runAction(() => respond(a.id, "accept"), "Accepted")}
                  >
                    Accept
                  </button>
                  <button
                    className="btn btn-sm btn-outline-danger"
                    onClick={() => setDeclining(a.id)}
                  >
                    Decline
                  </button>
                </AssignmentRow>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="card shadow-card">
        <div className="card-body">
          <h5 className="card-title">History</h5>
          {history.length === 0 ? (
            <p className="text-muted mb-0">No past or current assignments.</p>
          ) : (
            <ul className="list-group">
              {history.map((a) => (
                <AssignmentRow key={a.id} a={a}>
                  {a.status === "accepted" && (
                    <button
                      className="btn btn-sm btn-outline-secondary"
                      onClick={() => runAction(() => cancel(a.id), "Cancelled")}
                    >
                      Withdraw
                    </button>
                  )}
                </AssignmentRow>
              ))}
            </ul>
          )}
        </div>
      </div>

      {declining && (
        <div className="modal d-block" tabIndex="-1" role="dialog" style={{ background: "rgba(0,0,0,.3)" }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Decline assignment</h5>
                <button className="btn-close" onClick={() => setDeclining(null)} />
              </div>
              <div className="modal-body">
                <label className="form-label small">Reason (optional)</label>
                <input
                  className="form-control"
                  value={declineReason}
                  onChange={(e) => setDeclineReason(e.target.value)}
                  placeholder="Let the team know why"
                />
              </div>
              <div className="modal-footer">
                <button className="btn btn-light" onClick={() => setDeclining(null)}>
                  Cancel
                </button>
                <button className="btn btn-danger" onClick={submitDecline}>
                  Decline
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
