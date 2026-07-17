// src/components/home/useApiList.js

import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API || "http://127.0.0.1:8000/api";

export default function useApiList(path) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    fetch(`${API}${path}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((j) => alive && setData(Array.isArray(j) ? j : []))
      .catch(() => alive && setErr("Error"))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [path]);

  return { data, loading, err };
}

// Helpers
export const normalizeGallery = (g) => {
  if (!Array.isArray(g)) return [];
  return g
    .map((it, i) => {
      if (typeof it === "string") return { url: it, tag: "", position: i };
      const pos = Number.isFinite(Number(it?.position)) ? Number(it.position) : i;
      return { url: it?.url, tag: it?.tag || "", position: pos };
    })
    .filter((x) => !!x.url)
    .sort((a, b) => a.position - b.position);
};
