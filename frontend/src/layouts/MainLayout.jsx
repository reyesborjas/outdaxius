// frontend/src/layouts/MainLayout.jsx
import { useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate, Outlet, useParams, Link, useLocation, Navigate } from "react-router-dom";
import "../styles/role-theme.css";


export default function MainLayout() {
  const { logout, user, loading } = useAuth();
  const { email } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const role = user?.role;
  const isAdminOrGuide = role === "admin" || role === "guide";
  const paramEmail = decodeURIComponent(email || "");

  // 🔁 Los hooks siempre deben ejecutarse en todos los renders
  useEffect(() => {
    if (!user) return;

    // Corrige la URL si el email no coincide
    if (paramEmail !== user.email) {
      navigate(`/main/${encodeURIComponent(user.email)}`, { replace: true });
      return;
    }

    // Si está exactamente en /main/:email, redirige home por rol
    if (location.pathname === `/main/${email}`) {
      if (role === "admin") navigate(`/main/${email}/admin-home`, { replace: true });
      if (role === "guide") navigate(`/main/${email}/guide-home`, { replace: true });
      // users se quedan en /main/:email
    }
  }, [user, paramEmail, navigate, location.pathname, role, email]);

  // ✅ Los returns condicionales van después de los hooks
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;

  const activitiesLink = isAdminOrGuide ? `/main/${email}/activities?manage=1` : `/main/${email}/activities`;
  const programsLink   = isAdminOrGuide ? `/main/${email}/programs?manage=1`   : `/main/${email}/programs`;
  const schedulesLink  = isAdminOrGuide ? `/main/${email}/schedules?manage=1`  : `/main/${email}/schedules`;
  const bookingsLink   = `/main/${email}/bookings`;

  return (
    <div className={`app-shell role-${role || "client"}`}>
      <aside className="app-sidebar d-flex flex-column p-3">
        <h1 className="text-h1 mb-1 role-heading">Outdaxius</h1>
        <div className="role-underline" />

        {role === "admin" && (
          <>
            <Link to={`/main/${email}/admin-home`} className="nav-link mb-2 role-link">Admin Home</Link>
            <Link to={activitiesLink} className="nav-link mb-2 role-link">View Activities</Link>
            <Link to={programsLink} className="nav-link mb-2 role-link">View Programs</Link>
            <Link to={schedulesLink} className="nav-link mb-2 role-link">View Schedules</Link>
            <Link to={bookingsLink} className="nav-link mb-2 role-link">View Bookings</Link>
            <Link to={`/main/${email}/create-activity`} className="nav-link mb-2 role-link">Create Activity</Link>
            <Link to={`/main/${email}/create-program`} className="nav-link mb-2 role-link">Create Program</Link>
            <Link to={`/main/${email}/create-schedule`} className="nav-link mb-2 role-link">Create Schedule</Link>
            <Link to={`/main/${email}/users`} className="nav-link mb-2 role-link">Manage Users</Link>
            <Link to={`/main/${email}/reports`} className="nav-link mb-2 role-link">Reports</Link>
            <Link to={`/main/${email}/refunds`} className="nav-link mb-2 role-link">Refund Queue</Link>

          </>
        )}

        {role === "guide" && (
          <>
            <Link to={`/main/${email}/guide-home`} className="nav-link mb-2 role-link">Guide Home</Link>
            <Link to={activitiesLink} className="nav-link mb-2 role-link">View Activities</Link>
            <Link to={programsLink} className="nav-link mb-2 role-link">View Programs</Link>
            <Link to={`/main/${email}/create-activity`} className="nav-link mb-2 role-link">Create Activity</Link>
            <Link to={`/main/${email}/create-program`} className="nav-link mb-2 role-link">Create Program</Link>
            <Link to={`/main/${email}/create-schedule`} className="nav-link mb-2 role-link">Create Schedule</Link>
            <Link to={schedulesLink} className="nav-link mb-2 role-link">View Schedules</Link>
            <Link to={bookingsLink} className="nav-link mb-2 role-link">View Bookings</Link>
            <Link to={`/main/${email}/profile`} className="nav-link mb-2 role-link">My Profile</Link>
            <Link to={`/main/${email}/users`} className="nav-link mb-2 role-link">Manage Users</Link>
            <Link to={`/main/${email}/companies`} className="nav-link mb-2 role-link">My Companies</Link>
            <Link to={`/main/${email}/membership-requests`} className="nav-link mb-2 role-link">Team Membership</Link>
          </>
        )}

        {role === "client" && (
          <>
            <Link to={`/main/${email}`} className="nav-link mb-2 role-link">Home</Link>
            <Link to={activitiesLink} className="nav-link mb-2 role-link">Search Activities</Link>
            <Link to={programsLink} className="nav-link mb-2 role-link">Search Programs</Link>
            <Link to={bookingsLink} className="nav-link mb-2 role-link">My Bookings</Link>
            <Link to={`/main/${email}/trips`} className="nav-link mb-2 role-link">Search Trips</Link>
            <Link to={`/main/${email}/profile`} className="nav-link mb-2 role-link">My Profile</Link>
          </>
        )}

        <button
          onClick={() => { logout(); navigate("/"); }}
          className="btn btn-danger mt-auto"
        >
          Sign Out
        </button>
      </aside>

      <main className="app-main" style={{ minWidth: 0 }}>
        <Outlet />
        
      </main>
    </div>
  );
}
