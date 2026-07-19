// frontend/src/context/ToastContext.jsx
import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

const ToastContext = createContext(null);
export const useToast = () => useContext(ToastContext);

const VARIANT_STYLES = {
  success: { background: "#1E8449", icon: "✓" },
  error: { background: "#E74C3C", icon: "✕" },
  info: { background: "#2C3E50", icon: "ℹ" },
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const idRef = useRef(0);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback(
    (message, variant = "info", { duration = 5000 } = {}) => {
      const id = ++idRef.current;
      setToasts((prev) => [...prev, { id, message, variant }]);
      if (duration > 0) {
        setTimeout(() => dismiss(id), duration);
      }
      return id;
    },
    [dismiss]
  );

  const value = useMemo(
    () => ({
      show,
      success: (message, opts) => show(message, "success", opts),
      error: (message, opts) => show(message, "error", opts),
      info: (message, opts) => show(message, "info", opts),
      dismiss,
    }),
    [show, dismiss]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        style={{
          position: "fixed",
          top: 16,
          right: 16,
          zIndex: 2000,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          maxWidth: 360,
        }}
      >
        {toasts.map((t) => {
          const style = VARIANT_STYLES[t.variant] || VARIANT_STYLES.info;
          return (
            <div
              key={t.id}
              role="alert"
              style={{
                background: style.background,
                color: "#fff",
                padding: "12px 16px",
                borderRadius: "0.5rem",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.15)",
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                fontSize: "0.9rem",
                lineHeight: 1.4,
              }}
            >
              <span aria-hidden="true">{style.icon}</span>
              <span style={{ flex: 1, whiteSpace: "pre-wrap" }}>{t.message}</span>
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                aria-label="Close"
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#fff",
                  opacity: 0.8,
                  cursor: "pointer",
                  fontSize: "1rem",
                  lineHeight: 1,
                  padding: 0,
                }}
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
