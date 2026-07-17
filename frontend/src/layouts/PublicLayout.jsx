// frontend/src/layouts/PublicLayout.jsx
import PublicHeader from "../components/PublicHeader";

export default function PublicLayout({ children }) {
  return (
    <div className="min-vh-100 d-flex flex-column bg-surface-snow">
      <PublicHeader />
      <main className="flex-grow-1">{children}</main>
    </div>
  );
}
