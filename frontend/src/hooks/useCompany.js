// frontend/src/hooks/useCompany.js
import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";

const API = (import.meta.env.VITE_API ?? "http://127.0.0.1:8000/api").replace(/\/$/, "");
const join = (p) => `${API}${p.startsWith("/") ? "" : "/"}${p}`;

export function useCompany(companyId) {
  const { token } = useAuth();
  const [company, setCompany] = useState(null);
  const [license, setLicense] = useState(null);
  const [members, setMembers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchCompany = useCallback(async () => {
    if (!companyId || !token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(join(`/companies/${companyId}`), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      setCompany(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [companyId, token]);

  const fetchLicense = useCallback(async () => {
    if (!companyId || !token) return;
    try {
      const res = await fetch(join(`/companies/${companyId}/license`), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      setLicense(data);
    } catch (err) {
      console.error("Error fetching license:", err);
    }
  }, [companyId, token]);

  const fetchMembers = useCallback(async () => {
    if (!companyId || !token) return;
    try {
      const res = await fetch(join(`/companies/${companyId}/members`), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      setMembers(data);
    } catch (err) {
      console.error("Error fetching members:", err);
    }
  }, [companyId, token]);

  const fetchInvitations = useCallback(async () => {
    if (!companyId || !token) return;
    try {
      const res = await fetch(join(`/companies/${companyId}/invitations`), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      setInvitations(data);
    } catch (err) {
      console.error("Error fetching invitations:", err);
    }
  }, [companyId, token]);

  const createInvitation = useCallback(
    async (email, expiresInDays = 7) => {
      if (!companyId || !token) throw new Error("Missing company or token");
      
      const res = await fetch(join(`/companies/${companyId}/invitations`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          invited_email: email,
          expires_in_days: expiresInDays,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Error ${res.status}`);
      }

      const invitation = await res.json();
      await fetchInvitations(); // Refresh list
      return invitation;
    },
    [companyId, token, fetchInvitations]
  );

  const acceptInvitation = useCallback(
    async (code) => {
      if (!token) throw new Error("Not authenticated");
      
      const res = await fetch(join("/companies/invitations/accept"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ code }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Error ${res.status}`);
      }

      return res.json();
    },
    [token]
  );

  const removeMember = useCallback(
    async (userId) => {
      if (!companyId || !token) throw new Error("Missing company or token");
      
      const res = await fetch(join(`/companies/${companyId}/members/${userId}`), {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Error ${res.status}`);
      }

      await fetchMembers(); // Refresh list
    },
    [companyId, token, fetchMembers]
  );

  useEffect(() => {
    if (companyId && token) {
      fetchCompany();
      fetchLicense();
      fetchMembers();
      fetchInvitations();
    }
  }, [companyId, token, fetchCompany, fetchLicense, fetchMembers, fetchInvitations]);

  return {
    company,
    license,
    members,
    invitations,
    loading,
    error,
    refresh: fetchCompany,
    createInvitation,
    acceptInvitation,
    removeMember,
  };
}