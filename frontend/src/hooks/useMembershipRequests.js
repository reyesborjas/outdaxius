// frontend/src/hooks/useMembershipRequests.js
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

export function useMembershipRequests() {
  const { token } = useAuth();
  const [incoming, setIncoming] = useState([]);
  const [outgoing, setOutgoing] = useState([]);
  const [teamPending, setTeamPending] = useState([]);
  const [departure, setDeparture] = useState({ can_leave: true, reason: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const [mine, dep] = await Promise.all([
        api.get("/membership-requests/mine"),
        api.get("/membership-requests/departure-status"),
      ]);
      setIncoming(mine.incoming || []);
      setOutgoing(mine.outgoing || []);
      setTeamPending(mine.team_pending || []);
      setDeparture(dep || { can_leave: true, reason: null });
    } catch (e) {
      setError(e.message || "Error loading membership requests");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const invite = useCallback(
    async ({ teamId, targetUserId, targetEmail, offeredLevel = 4, message, onBehalfOfCompanyId }) => {
      const req = await api.post("/membership-requests/invite", {
        team_id: teamId,
        target_user_id: targetUserId || null,
        target_email: targetEmail || null,
        offered_level: offeredLevel,
        message: message || null,
        on_behalf_of_company_id: onBehalfOfCompanyId || null,
      });
      await refresh();
      return req;
    },
    [refresh]
  );

  const apply = useCallback(
    async ({ teamId, message }) => {
      const req = await api.post("/membership-requests/apply", { team_id: teamId, message: message || null });
      await refresh();
      return req;
    },
    [refresh]
  );

  const consent = useCallback(
    async (requestId, decision) => {
      const req = await api.post(`/membership-requests/${requestId}/consent`, { decision });
      await refresh();
      return req;
    },
    [refresh]
  );

  const accept = useCallback(
    async (requestId) => {
      const req = await api.post(`/membership-requests/${requestId}/accept`);
      await refresh();
      return req;
    },
    [refresh]
  );

  const reject = useCallback(
    async (requestId) => {
      const req = await api.post(`/membership-requests/${requestId}/reject`);
      await refresh();
      return req;
    },
    [refresh]
  );

  const cancel = useCallback(
    async (requestId) => {
      const req = await api.post(`/membership-requests/${requestId}/cancel`);
      await refresh();
      return req;
    },
    [refresh]
  );

  const leaveTeam = useCallback(async () => {
    await api.post("/membership-requests/leave-team");
    await refresh();
  }, [refresh]);

  return {
    incoming,
    outgoing,
    teamPending,
    departure,
    loading,
    error,
    refresh,
    invite,
    apply,
    consent,
    accept,
    reject,
    cancel,
    leaveTeam,
  };
}
