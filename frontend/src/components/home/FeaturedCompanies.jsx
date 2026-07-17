// src/components/home/FeaturedCompanies.jsx
import React from "react";

const companies = [
  { name: "Andes Trek Co.", logo: null },
  { name: "Patagonia Kayaks", logo: null },
  { name: "Desert Guides", logo: null },
  { name: "Volcano Tours", logo: null },
  { name: "Coastline Surf", logo: null },
  { name: "Glacier Ops", logo: null },
];

export default function FeaturedCompanies() {
  return (
    <div className="row row-cols-2 row-cols-md-3 row-cols-lg-6 g-3 align-items-center">
      {companies.map((c, i) => (
        <div className="col text-center" key={i}>
          <div className="border rounded-3 py-4 px-3 bg-white h-100 d-flex align-items-center justify-content-center">
            {c.logo ? (
              <img src={c.logo} alt={c.name} style={{ maxHeight: 38, maxWidth: "100%" }} />
            ) : (
              <span className="text-muted small">{c.name}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
