// src/components/common/OneRowCarousel.jsx
import React, { useRef } from "react";

export default function OneRowCarousel({ children, className = "" }) {
  const ref = useRef(null);
  const scrollBy = (dir) => {
    const el = ref.current; if (!el) return;
    const dx = Math.round(el.clientWidth * 0.9) * (dir === "left" ? -1 : 1);
    el.scrollBy({ left: dx, behavior: "smooth" });
  };
  return (
    <div className={className}>
      <div className="d-flex justify-content-between align-items-end mb-3">
        <div></div>
        <div className="d-flex gap-2">
          <button className="btn btn-outline-secondary btn-sm" onClick={() => scrollBy("left")} aria-label="Prev">‹</button>
          <button className="btn btn-outline-secondary btn-sm" onClick={() => scrollBy("right")} aria-label="Next">›</button>
        </div>
      </div>
      <div
        ref={ref}
        style={{ whiteSpace: "nowrap", overflowX: "auto", scrollbarWidth: "thin", paddingBottom: 6 }}
      >
        {children}
      </div>
    </div>
  );
}
