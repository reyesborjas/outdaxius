// src/components/home/useApiList.js

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function useApiList(path) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api
      .get(path, { skipAuth: true })
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
