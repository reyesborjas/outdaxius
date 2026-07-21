// frontend/src/hooks/useAssignments.js
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

export function useAssignments() {
  const { token } = useAuth();
  const [incoming, setIncoming] = useState([]);
  const [mine, setMine] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.get("/assignments/mine");
      setIncoming(data.incoming || []);
      setMine(data.mine || []);
    } catch (e) {
      setError(e.message || "Error loading assignments");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const respond = useCallback(
    async (assignmentId, decision, declineReason) => {
      const a = await api.post(`/assignments/${assignmentId}/respond`, {
        decision,
        decline_reason: declineReason || null,
      });
      await refresh();
      return a;
    },
    [refresh]
  );

  const cancel = useCallback(
    async (assignmentId) => {
      const a = await api.post(`/assignments/${assignmentId}/cancel`);
      await refresh();
      return a;
    },
    [refresh]
  );

  return { incoming, mine, loading, error, refresh, respond, cancel };
}

export async function fetchScheduleAssignments(activityScheduleId) {
  return api.get(`/assignments/schedule/${activityScheduleId}`);
}

export async function selfAssign(activityScheduleId, isLeader) {
  return api.post("/assignments/self-assign", {
    activity_schedule_id: activityScheduleId,
    is_leader: isLeader,
  });
}

export async function proposeAssignment(activityScheduleId, userId, isLeader) {
  return api.post("/assignments/propose", {
    activity_schedule_id: activityScheduleId,
    user_id: userId,
    is_leader: isLeader,
  });
}

export async function cancelAssignment(assignmentId) {
  return api.post(`/assignments/${assignmentId}/cancel`);
}
