// src/components/Home/PlatformFeatures.jsx
import React from "react";

const features = [
  { title: "Freemium → Premium", desc: "Empieza gratis. Escala cuando vendas más." },
  { title: "7% comisión", desc: "Modelo claro y competitivo para reservas." },
  { title: "GDPR & privacidad", desc: "Borrado/portabilidad de datos desde el MVP." },
  { title: "Gestión de reservas", desc: "Programas, actividades, cupos y asistentes." },
  { title: "Roles y permisos", desc: "Admin, guía y viajero listos para operar." },
  { title: "Mapa & ‘Near me’", desc: "PostGIS listo para búsquedas geoespaciales." },
];

export default function PlatformFeatures() {
  return (
    <div className="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-3">
      {features.map((f, i) => (
        <div className="col" key={i}>
          <div className="card h-100 border-200 shadow-sm">
            <div className="card-body">
              <h5 className="fw-semibold mb-2">{f.title}</h5>
              <p className="text-muted mb-0">{f.desc}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
