// frontend/src/App.jsx
import { Routes, Route } from "react-router-dom";
import MainLayout from "./layouts/MainLayout";
import PublicLayout from "./layouts/PublicLayout";
import ProtectedRoute from "./components/ProtectedRoute";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Activities from "./pages/Activities";
import Programs from "./pages/Programs";
import About from "./pages/About";

import UserHome from "./pages/UserHome";
import GuideHome from "./pages/GuideHome";
import AdminHome from "./pages/AdminHome";

import ManageUsers from "./pages/ManageUsers";
import Reports from "./pages/Reports";
import ManagePrograms from "./pages/ManagePrograms";
import CreateActivity from "./pages/CreateActivity";
import CreateProgram from "./pages/CreateProgram";
import SearchTrips from "./pages/SearchTrips";

import Schedules from "./pages/Schedules";
import Bookings from "./pages/Bookings";
import CreateSchedule from "./pages/CreateSchedule";

import ProfileEditor from "./components/ProfileEditor";

import CreateCompany from "./pages/CreateCompany";
import MyCompanies from "./pages/MyCompanies";
import CompanyDashboard from "./pages/CompanyDashboard";
import AcceptInvitation from "./pages/AcceptInvitation";
import RefundQueue from "./pages/RefundQueue";
import MembershipRequests from "./pages/MembershipRequests";
import Assignments from "./pages/Assignments";

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<PublicLayout><Home /></PublicLayout>} />
      <Route path="/login" element={<PublicLayout><Login /></PublicLayout>} />
      <Route path="/register" element={<PublicLayout><Register /></PublicLayout>} />
      <Route path="/activities" element={<PublicLayout><Activities /></PublicLayout>} />
      <Route path="/programs" element={<PublicLayout><Programs /></PublicLayout>} />
      <Route path="/about" element={<PublicLayout><About /></PublicLayout>} />
       <Route path="/accept-invitation" element={<AcceptInvitation />} />
      {/* Dashboard (MainLayout, /main/:email) — gated behind auth */}
      <Route element={<ProtectedRoute />}>
        <Route path="/main/:email" element={<MainLayout />}>
        <Route path="profile" element={<ProfileEditor />} />
          {/* User */}
          <Route index element={<UserHome />} />
          <Route path="trips" element={<SearchTrips />} />

          {/* Guide */}
          <Route path="guide-home" element={<GuideHome />} />
          <Route path="manage-programs" element={<ManagePrograms />} />

          {/* Company */}
          {/* 🔥 NUEVAS: Rutas de empresas */}
          <Route path="companies" element={<MyCompanies />} />
          <Route path="create-company" element={<CreateCompany />} />
          <Route path="company/:companyId" element={<CompanyDashboard />} />
          <Route path="membership-requests" element={<MembershipRequests />} />
          <Route path="assignments" element={<Assignments />} />

          {/* Admin */}
          <Route path="admin-home" element={<AdminHome />} />
          <Route element={<ProtectedRoute roles={["admin"]} />}>
            <Route path="users" element={<ManageUsers />} />
            <Route path="reports" element={<Reports />} />
            <Route path="refunds" element={<RefundQueue />} />
          </Route>

          {/* Shared */}
          <Route path="activities" element={<Activities />} />
          <Route path="programs" element={<Programs />} />
          <Route path="create-activity" element={<CreateActivity />} />
          <Route path="create-program" element={<CreateProgram />} />
          <Route path="schedules" element={<Schedules />} />
          <Route path="bookings" element={<Bookings />} />
          <Route path="create-schedule" element={<CreateSchedule />} />
          {/* edit routes removed → handled via modals */}
        </Route>
      </Route>
    </Routes>
  );
}
