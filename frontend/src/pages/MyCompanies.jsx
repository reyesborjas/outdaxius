// frontend/src/pages/MyCompanies.jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const API = (import.meta.env.VITE_API ?? "http://127.0.0.1:8000/api").replace(/\/$/, "");
const join = (p) => `${API}${p.startsWith("/") ? "" : "/"}${p}`;

export default function MyCompanies() {
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    
    const fetchCompanies = async () => {
      try {
        const res = await fetch(join("/companies"), {
          headers: { Authorization: `Bearer ${token}` },
        });
        
        if (!res.ok) throw new Error(`Error ${res.status}`);
        
        const data = await res.json();
        setCompanies(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchCompanies();
  }, [token]);

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

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2 className="text-h2 mb-0">My Companies</h2>
        {user?.role === "guide" && (
          <button
            className="btn btn-primary"
            onClick={() => navigate(`/main/${encodeURIComponent(user.email)}/create-company`)}
          >
            + Create Company
          </button>
        )}
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {companies.length === 0 ? (
        <div className="card shadow-card">
          <div className="card-body text-center py-5">
            <p className="text-muted mb-3">You are not a member of any companies yet.</p>
            {user?.role === "guide" && (
              <button
                className="btn btn-primary"
                onClick={() => navigate(`/main/${encodeURIComponent(user.email)}/create-company`)}
              >
                Create Your First Company
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
          {companies.map((company) => (
            <div key={company.id} className="col">
              <div className="card shadow-card h-100">
                <div className="card-body">
                  <h5 className="card-title">{company.name}</h5>
                  <p className="card-text text-muted small">
                    {company.description || "No description"}
                  </p>
                  
                  <div className="d-flex justify-content-between align-items-center mt-3">
                    <span className={`badge ${company.is_active ? 'bg-success' : 'bg-danger'}`}>
                      {company.is_active ? 'Active' : 'Inactive'}
                    </span>
                    <span className="badge bg-primary">
                      {company.license_tier || 'free'}
                    </span>
                  </div>
                </div>
                <div className="card-footer bg-transparent">
                  <button
                    className="btn btn-outline-primary w-100"
                    onClick={() =>
                      navigate(`/main/${encodeURIComponent(user.email)}/company/${company.id}`)
                    }
                  >
                    View Dashboard
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}