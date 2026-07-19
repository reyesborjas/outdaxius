// frontend/src/hooks/useCompany.js
import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

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
      const data = await api.get(`/companies/${companyId}`);
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
      const data = await api.get(`/companies/${companyId}/license`);
      setLicense(data);
    } catch (err) {
      console.error("Error fetching license:", err);
    }
  }, [companyId, token]);

  const fetchMembers = useCallback(async () => {
    if (!companyId || !token) return;
    try {
      const data = await api.get(`/companies/${companyId}/members`);
      setMembers(data);
    } catch (err) {
      console.error("Error fetching members:", err);
    }
  }, [companyId, token]);

  const fetchInvitations = useCallback(async () => {
    if (!companyId || !token) return;
    try {
      const data = await api.get(`/companies/${companyId}/invitations`);
      setInvitations(data);
    } catch (err) {
      console.error("Error fetching invitations:", err);
    }
  }, [companyId, token]);

  const createInvitation = useCallback(
    async (email, expiresInDays = 7) => {
      if (!companyId || !token) throw new Error("Missing company or token");

      const invitation = await api.post(`/companies/${companyId}/invitations`, {
        invited_email: email,
        expires_in_days: expiresInDays,
      });
      await fetchInvitations(); // Refresh list
      return invitation;
    },
    [companyId, token, fetchInvitations]
  );

  const acceptInvitation = useCallback(
    async (code) => {
      if (!token) throw new Error("Not authenticated");
      return api.post("/companies/invitations/accept", { code });
    },
    [token]
  );

  const removeMember = useCallback(
    async (userId) => {
      if (!companyId || !token) throw new Error("Missing company or token");
      await api.delete(`/companies/${companyId}/members/${userId}`);
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