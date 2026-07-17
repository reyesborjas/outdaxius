// ===============================
// src/components/home/SearchableSelect.jsx
// ===============================
import { useState, useRef, useEffect } from "react";

export default function SearchableSelect({ 
  options = [], 
  value, 
  onChange, 
  placeholder = "Select...",
  loading = false,
  disabled = false,
  className = ""
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef(null);

  const filtered = options.filter(opt => 
    opt.label.toLowerCase().includes(search.toLowerCase())
  );

  const selected = options.find(opt => opt.value === value);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
        setSearch("");
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className={`position-relative ${className}`}>
      <div 
        className={`form-control d-flex justify-content-between align-items-center ${disabled ? 'bg-light' : 'cursor-pointer'}`}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        style={{ cursor: disabled ? 'not-allowed' : 'pointer' }}
      >
        <span className={selected ? "" : "text-muted"}>
          {loading ? "Loading..." : (selected ? selected.label : placeholder)}
        </span>
        <span>▼</span>
      </div>

      {isOpen && !disabled && (
        <div className="position-absolute w-100 bg-white border rounded shadow-lg" 
             style={{ zIndex: 1000, maxHeight: 300, overflowY: 'auto', top: '100%', marginTop: 4 }}>
          <div className="p-2 border-bottom sticky-top bg-white">
            <input
              type="text"
              className="form-control form-control-sm"
              placeholder="Search..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>
          <div>
            {filtered.length === 0 ? (
              <div className="p-3 text-muted text-center">No results</div>
            ) : (
              filtered.map(opt => (
                <div
                  key={opt.value}
                  className={`px-3 py-2 cursor-pointer ${opt.value === value ? 'bg-primary text-white' : 'hover-bg-light'}`}
                  onClick={() => {
                    onChange(opt.value);
                    setIsOpen(false);
                    setSearch("");
                  }}
                  style={{ cursor: 'pointer' }}
                  onMouseEnter={(e) => {
                    if (opt.value !== value) {
                      e.currentTarget.style.backgroundColor = '#f8f9fa';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (opt.value !== value) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  {opt.label}
                  {opt.badge && (
                    <span className="badge bg-secondary ms-2 small">{opt.badge}</span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}