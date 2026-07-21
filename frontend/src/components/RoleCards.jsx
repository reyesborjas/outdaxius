// components/RoleCards.jsx
import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "../styles/role-theme.css"; 
export default function RoleCards() {
  const { user } = useAuth();
  const email = user?.email ? encodeURIComponent(user.email) : null;

  const cards = [
    { key: "admin",  title: "Admins",    desc: "Control & oversight." },
    { key: "guide",  title: "Guides",    desc: "Create and host." },
    { key: "client", title: "Travelers", desc: "Discover & book." },
  ];

  return (
    <section className="role-cards">
      {cards.map(c => (
        <article key={c.key} className={`role-card role-card--${c.key}`}>
          <h3>{c.title}</h3>
          <p>{c.desc}</p>
          <div className="bar" />
          {/* Si hay sesión y el rol coincide, muestra acceso al dashboard */}
          {user?.role === c.key && email && (
            <Link className="cta" to={`/main/${email}`}>Open dashboard →</Link>
          )}
        </article>
      ))}
    </section>
  );
}
