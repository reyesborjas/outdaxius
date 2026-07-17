// frontend/src/pages/Teams.jsx
import React, { useEffect, useState } from "react";
import useAuth from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

const API = import.meta.env.VITE_API || "http://127.0.0.1:8000/api";

export default function Teams() {
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const [teams, setTeams] = useState([]);
  const [members, setMembers] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [newTeamName, setNewTeamName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState();

  // Listar equipos del usuario actual
  useEffect(() => {
    if (!token) return;
    fetch(`${API}/teams`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.ok ? r.json() : Promise.reject("Error loading teams"))
      .then(setTeams)
      .catch(() => setTeams([]));
  }, [token, creating]);

  // Listar miembros al seleccionar un equipo
  useEffect(() => {
    if (!token || !selectedTeam) return;
    fetch(`${API}/teams/${selectedTeam.id}/members`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.ok ? r.json() : Promise.reject("Error loading members"))
      .then(setMembers)
      .catch(() => setMembers([]));
  }, [token, selectedTeam]);

  // Crear un nuevo equipo
  const handleCreateTeam = async (e) => {
    e.preventDefault();
    setError("");
    if (!newTeamName.trim()) {
      setError("Debes ingresar un nombre de equipo.");
      return;
    }
    setCreating(true);
    try {
      const res = await fetch(`${API}/teams`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: newTeamName }),
      });
      if (!res.ok) {
        let detail = "Error creando equipo";
        try {
          const err = await res.json();
          detail = err.detail || detail;
        } catch {}
        throw new Error(detail);
      }
      setNewTeamName("");
    } catch (e) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="container py-4">
      <div className="card shadow-card rounded-xl2">
        <div className="card-body">
          <h2 className="text-h2 mb-4">Equipos de trabajo</h2>

          <form onSubmit={handleCreateTeam} className="mb-4">
            <div className="row g-2 align-items-end">
              <div className="col-md-6">
                <label className="form-label">Nuevo equipo</label>
                <input
                  className="form-control"
                  value={newTeamName}
                  onChange={e => setNewTeamName(e.target.value)}
                  placeholder="Nombre del equipo"
                  disabled={creating}
                />
              </div>
              <div className="col-md-3">
                <button type="submit" className="btn btn-primary" disabled={creating}>
                  {creating ? "Creando..." : "Crear"}
                </button>
              </div>
              {error && <div className="col-12"><div className="alert alert-danger">{error}</div></div>}
            </div>
          </form>

          <h5 className="fw-semibold mb-3">Tus equipos</h5>
          <ul className="list-group mb-3">
            {teams.length === 0 && <li className="list-group-item">No tienes equipos creados</li>}
            {teams.map(team => (
              <li key={team.id} className={`list-group-item${selectedTeam?.id === team.id ? " active" : ""}`}
                style={{ cursor: "pointer" }}
                onClick={() => setSelectedTeam(team)}
              >
                {team.name}
              </li>
            ))}
          </ul>

          {selectedTeam && (
            <>
              <h5 className="fw-semibold mt-4 mb-2">Miembros de {selectedTeam.name}</h5>
              {members.length === 0
                ? <p className="text-muted">No hay miembros asignados aún</p>
                : (
                  <ul className="list-group">
                    {members.map(m => (
                      <li key={m.user_id} className="list-group-item">{m.user_id}</li>
                    ))}
                  </ul>
                )
              }
            </>
          )}
        </div>
      </div>
    </div>
  );
}
