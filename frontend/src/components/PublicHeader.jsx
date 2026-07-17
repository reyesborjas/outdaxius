// src/components/PublicHeader.jsx
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import logo from "../assets/logo.png";

export default function PublicHeader() {
  const { user } = useAuth();
  const dashHref = user ? `/main/${encodeURIComponent(user.email)}` : "/main";

  return (
    <header className="border-bottom bg-surface-snow shadow-card">
      <div className="container-xl d-flex align-items-center justify-content-between py-3">
        <div className="d-flex align-items-center gap-2 flex-shrink-0">
          <Link to="/"><img src={logo} alt="Outdaxius Logo" style={{ height: "55px" }} /></Link>
          <h1 className="text-h2 text-role-admin mb-0">Outdaxius</h1>
        </div>
        <nav className="d-flex align-items-center gap-3 text-body fw-medium">
          {!user && <Link to="/login" className="text-role-admin text-decoration-none">Login</Link>}
          {user && <Link to={dashHref} className="text-role-admin text-decoration-none">Dashboard</Link>}
          <Link to="/register" className="text-role-guide text-decoration-none">Register</Link>
          <Link to="/about" className="text-state-neutral text-decoration-none">About</Link>
          <Link to="/programs" className="text-role-traveler text-decoration-none">Programs</Link>
          <Link to="/activities" className="text-role-traveler text-decoration-none">Activities</Link>
        </nav>
      </div>
    </header>
  );
}
