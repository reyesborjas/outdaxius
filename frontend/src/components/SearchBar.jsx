import React, { useState } from "react";

export default function SearchBar({
  value,
  onChange,
  onSearch,
  onClear,
  loading = false,
  placeholder = "Search…",
  className = "",
}) {
  const [local, setLocal] = useState(value || "");

  const fire = () => {
    const q = (local ?? "").trim();
    if (!q) return onClear?.();
    onSearch?.({query: q});
    
  };

  return (
    <div className={`d-flex w-100 ${className}`}>
      <input
        className="form-control flex-grow-1 me-2"
        value={local}
        onChange={(e) => {
          setLocal(e.target.value);
          onChange?.(e.target.value);
        }}
        onKeyDown={(e) => e.key === "Enter" && fire()}
        placeholder={placeholder}
      />
      {local ? (
        <button
          type="button"
          className="btn btn-outline-secondary me-2"
          onClick={() => {
            setLocal("");
            onChange?.("");
            onClear?.();
          }}
          title="Clear"
        >
          ✕
        </button>
      ) : null}
      <button
        type="button"
        className="btn btn-primary"
        onClick={fire}
        disabled={loading}
      >
        {loading ? "Searching…" : "Search"}
      </button>
    </div>
  );
}
