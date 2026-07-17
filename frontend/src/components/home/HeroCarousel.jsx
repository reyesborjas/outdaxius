import React, { useEffect, useMemo, useState } from "react";
import useApiList, { normalizeGallery } from "./useApiList.js";

export default function HeroCarousel() {
  const { data: acts } = useApiList("/activities");
  const { data: progs } = useApiList("/programs/");

  const slides = useMemo(() => {
    const imgs = [];
    for (const a of acts || []) imgs.push(...normalizeGallery(a?.gallery));
    for (const p of progs || []) imgs.push(...normalizeGallery(p?.gallery));
    // fallback: solo primeras 12 para performance
    return imgs.slice(0, 12);
  }, [acts, progs]);

  const [idx, setIdx] = useState(0);
  const n = slides.length;

  useEffect(() => {
    if (!n) return;
    const t = setInterval(() => setIdx((i) => (i + 1) % n), 4000);
    return () => clearInterval(t);
  }, [n]);

  if (!n) {
    return (
      <div className="ratio ratio-21x9 bg-body-tertiary rounded-3 d-flex align-items-center justify-content-center">
        <div className="text-muted">No images available</div>
      </div>
    );
  }

  const prev = () => setIdx((i) => (i - 1 + n) % n);
  const next = () => setIdx((i) => (i + 1) % n);

  const left = (idx - 1 + n) % n;
  const right = (idx + 1) % n;

  return (
    <div className="position-relative">
      <div className="d-flex justify-content-center align-items-end gap-3">
        <img
          src={slides[left].url}
          alt={slides[left].tag || "left"}
          onClick={prev}
          style={{ width: 220, height: 120, objectFit: "cover", borderRadius: 12, opacity: 0.85, cursor: "pointer" }}
        />
        <img
          src={slides[idx].url}
          alt={slides[idx].tag || "center"}
          style={{ width: "100%", maxWidth: 960, height: 200, objectFit: "cover", borderRadius: 16, boxShadow: "0 8px 24px rgba(0,0,0,0.25)" }}
        />
        <img
          src={slides[right].url}
          alt={slides[right].tag || "right"}
          onClick={next}
          style={{ width: 220, height: 120, objectFit: "cover", borderRadius: 12, opacity: 0.85, cursor: "pointer" }}
        />
      </div>
      <button className="btn btn-light position-absolute top-50 start-0 translate-middle-y" onClick={prev} aria-label="Prev">‹</button>
      <button className="btn btn-light position-absolute top-50 end-0 translate-middle-y" onClick={next} aria-label="Next">›</button>
    </div>
  );
}
