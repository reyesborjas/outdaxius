import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate, Link } from "react-router-dom";

const EMAIL_RX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const { login, requestPasswordReset } = useAuth();
  const nav = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [fieldErr, setFieldErr] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [resetNotice, setResetNotice] = useState("");

  const validate = () => {
    const fe = { email: "", password: "" };
    if (!EMAIL_RX.test(email)) fe.email = "Email inválido";
    if (password.length < 8) fe.password = "Mínimo 8 caracteres";
    setFieldErr(fe);
    return !fe.email && !fe.password;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErr(""); setResetNotice("");
    if (!validate()) return;
    setLoading(true);
    try {
      const u = await login(email, password);
      if (u?.role === "admin" || u?.role === "guide") {
        nav(`/main/${encodeURIComponent(u.email)}`, { replace: true });
      } else {
        nav("/", { replace: true });
      }
    } catch (e) {
      setErr(e.message || "Error de inicio de sesión");
    } finally {
      setLoading(false);
    }
  };

  const onForgot = async () => {
    setErr(""); setResetNotice("");
    if (!EMAIL_RX.test(email)) {
      setFieldErr((p) => ({ ...p, email: "Ingresa un email válido para recuperar" }));
      return;
    }
    setLoading(true);
    try {
      await requestPasswordReset(email);
      setResetNotice("Si el email existe, se envió un enlace de recuperación.");
    } catch (e) {
      setErr(e.message || "No se pudo iniciar recuperación");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container py-5">
      <div className="row justify-content-center">
        <div className="col-md-5">
          <div className="card shadow-card rounded-xl2">
            <div className="card-body">
              <h2 className="text-h2 mb-3">Login</h2>

              {err && <p className="text-state-danger mb-2">{err}</p>}
              {resetNotice && <p className="text-state-success mb-2">{resetNotice}</p>}

              <form onSubmit={handleSubmit} noValidate>
                <div className="mb-2">
                  <input
                    type="email"
                    className={`form-control ${fieldErr.email ? "is-invalid" : ""}`}
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="username"
                    required
                  />
                  {fieldErr.email && <div className="invalid-feedback">{fieldErr.email}</div>}
                </div>

                <div className="mb-3">
                  <input
                    type="password"
                    className={`form-control ${fieldErr.password ? "is-invalid" : ""}`}
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    required
                  />
                  {fieldErr.password && <div className="invalid-feedback">{fieldErr.password}</div>}
                </div>

                <button type="submit" className="btn btn-primary w-100" disabled={loading}>
                  {loading ? <span className="spinner-border spinner-border-sm" role="status" /> : "Sign in"}
                </button>

                <div className="d-flex justify-content-between mt-3">
                  <button type="button" className="btn btn-link p-0" onClick={onForgot} disabled={loading}>
                    ¿Olvidaste tu contraseña?
                  </button>
                  <Link to="/register" className="btn btn-link p-0">Crear cuenta</Link>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
