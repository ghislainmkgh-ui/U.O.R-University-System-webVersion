import { AlertCircle, CheckCircle2, Eye, Github, LockKeyhole, Mail, Moon, ShieldCheck, Sun } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { apiRequest } from "../api/client.js";
import { resolvePostLoginLocation } from "../routes/lastLocation.js";
import { useAuth } from "../state/AuthContext.jsx";
import { usePreferences } from "../state/PreferencesContext.jsx";

export function LoginPage() {
  const auth = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { language, setLanguage, theme, toggleTheme, t } = usePreferences();
  const [identifier, setIdentifier] = useState(() => localStorage.getItem("uor_saved_identifier") || "");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(() => localStorage.getItem("uor_remember_login") === "true");
  const [showPassword, setShowPassword] = useState(false);
  const [notice, setNotice] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dialog, setDialog] = useState("");

  const oauthError = searchParams.get("error");
  const oauthHandoff = searchParams.get("oauth_handoff");
  const postLoginLocation = useMemo(() => resolvePostLoginLocation(location.state?.from), [location.state]);

  useEffect(() => {
    if (!oauthError) return;
    setNotice({ type: "error", message: oauthErrorMessage(oauthError, language), detail: `oauth:${oauthError}` });
    setSearchParams({}, { replace: true });
  }, [language, oauthError, setSearchParams]);

  useEffect(() => {
    if (!oauthHandoff) return;
    let alive = true;
    setLoading(true);
    setNotice({ type: "info", message: t("oauthStarting"), detail: "oauth:consume" });
    apiRequest("/api/auth/oauth/consume/", {
      method: "POST",
      body: JSON.stringify({ handoff: oauthHandoff }),
    })
      .then((payload) => {
        if (!alive) return;
        auth.acceptSession(payload.data);
        setNotice({ type: "success", message: t("oauthSuccess"), detail: "oauth:success" });
        navigate(postLoginLocation, { replace: true });
      })
      .catch((err) => {
        if (!alive) return;
        setNotice(errorNotice(err, "oauth_consume_failed"));
        setSearchParams({}, { replace: true });
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [auth, navigate, oauthHandoff, postLoginLocation, setSearchParams, t]);

  const canSubmit = useMemo(() => identifier.trim() && password.trim() && !loading, [identifier, password, loading]);

  if (auth.isAuthenticated) {
    return <Navigate to={postLoginLocation} replace />;
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (!identifier.trim() || !password.trim()) {
      setNotice({ type: "error", message: t("missingCredentials"), detail: "login:missing_credentials" });
      return;
    }
    setLoading(true);
    setNotice(null);
    try {
      await auth.login(identifier.trim(), password);
      if (remember) {
        localStorage.setItem("uor_remember_login", "true");
        localStorage.setItem("uor_saved_identifier", identifier.trim());
      } else {
        localStorage.removeItem("uor_remember_login");
        localStorage.removeItem("uor_saved_identifier");
      }
      navigate(postLoginLocation, { replace: true });
    } catch (err) {
      setNotice(errorNotice(err, "login_failed"));
    } finally {
      setLoading(false);
    }
  }

  async function startOAuth(provider) {
    const email = identifier.trim().toLowerCase();
    if (!looksLikeEmail(email)) {
      setNotice({ type: "error", message: t("oauthEmailRequired"), detail: `oauth:${provider}:missing_expected_email` });
      return;
    }
    setLoading(true);
    setNotice({ type: "info", message: t("oauthStarting"), detail: `oauth:${provider}:start` });
    try {
      const payload = await apiRequest("/api/auth/oauth/start/", {
        method: "POST",
        body: JSON.stringify({ provider, expected_email: email }),
      });
      window.location.assign(payload.data.auth_url);
    } catch (err) {
      setNotice(errorNotice(err, `oauth_${provider}_start_failed`));
      setLoading(false);
    }
  }

  return (
    <main className="login-screen modern-login">
      <section className="modern-login-card split-login-card">
        <div className="login-form-panel">
          <div className="login-top-actions">
            <div className="language-toggle" aria-label={t("language")}>
              <button type="button" className={language === "FR" ? "active" : ""} onClick={() => setLanguage("FR")}>
                FR
              </button>
              <button type="button" className={language === "EN" ? "active" : ""} onClick={() => setLanguage("EN")}>
                EN
              </button>
            </div>
            <button type="button" className="theme-button" title={theme === "dark" ? t("lightTheme") : t("darkTheme")} onClick={toggleTheme}>
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>

          <div className="login-compact-brand">
            <div className="login-brand-mark">
              <ShieldCheck size={28} />
            </div>
            <span>U.O.R University</span>
          </div>

          <div className="login-card-heading">
            <div className="login-lock">
              <LockKeyhole size={24} />
            </div>
            <div>
              <h2>{t("signIn")}</h2>
              <p>{t("loginSubtitle")}</p>
            </div>
          </div>

          <form onSubmit={onSubmit} className="modern-login-form">
            <label>
              <span>{t("identifier")}</span>
              <div className="login-input-wrap">
                <Mail size={18} />
                <input
                  value={identifier}
                  onChange={(event) => setIdentifier(event.target.value)}
                  placeholder={t("identifierPlaceholder")}
                  autoComplete="username"
                />
              </div>
            </label>

            <label>
              <span>{t("password")}</span>
              <div className="login-input-wrap">
                <LockKeyhole size={18} />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                />
                <button type="button" title={showPassword ? "Masquer" : "Afficher"} onClick={() => setShowPassword((value) => !value)}>
                  <Eye size={18} />
                </button>
              </div>
            </label>

            <div className="login-options-row">
              <label className="remember-line">
                <input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} />
                <span>{t("rememberMe")}</span>
              </label>
              <button type="button" className="link-button" onClick={() => setDialog("forgot")}>
                {t("forgotPassword")}
              </button>
            </div>

            {notice && <LoginNotice notice={notice} />}

            <button className="login-primary-button" disabled={!canSubmit}>
              <span>{loading ? t("signingIn") : t("signIn")}</span>
            </button>

            <button type="button" className="login-secondary-button" onClick={() => setDialog("access")}>
              {t("createAccount")}
            </button>

            <div className="or-divider">
              <i />
              <span>{t("or")}</span>
              <i />
            </div>

            <div className="social-login-row">
              <button type="button" onClick={() => startOAuth("google")} disabled={loading}>
                <b>G</b>
                <span>{t("continueGoogle")}</span>
              </button>
              <button type="button" onClick={() => startOAuth("github")} disabled={loading}>
                <Github size={22} />
                <span>{t("continueGithub")}</span>
              </button>
            </div>
          </form>
        </div>

        <aside className="login-visual-panel" aria-label={t("visualWelcome")}>
          <span className="visual-secure-pill">{t("visualBadge")}</span>
          <div className="visual-copy">
            <h1>{t("visualWelcome")}</h1>
          </div>
          <div className="visual-dots" aria-hidden="true">
            <i />
            <i />
            <i />
          </div>
        </aside>
      </section>

      {dialog === "forgot" && <ForgotPasswordDialog identifier={identifier} setIdentifier={setIdentifier} onClose={() => setDialog("")} onNotice={setNotice} />}
      {dialog === "access" && <AccessRequestDialog onClose={() => setDialog("")} onNotice={setNotice} />}
    </main>
  );
}

function LoginNotice({ notice }) {
  const Icon = notice.type === "success" ? CheckCircle2 : AlertCircle;
  return (
    <div className={`login-notice ${notice.type}`}>
      <Icon size={18} />
      <div>
        <strong>{notice.message}</strong>
      </div>
    </div>
  );
}

function ForgotPasswordDialog({ identifier, setIdentifier, onClose, onNotice }) {
  const { t } = usePreferences();
  const [form, setForm] = useState({ identifier: identifier || "", password: "", confirm: "" });
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setLocalError("");
    if (form.password.length < 4) {
      setLocalError(t("passwordTooShort"));
      return;
    }
    if (form.password !== form.confirm) {
      setLocalError(t("passwordMismatch"));
      return;
    }
    setBusy(true);
    try {
      const payload = await apiRequest("/api/auth/reset-password/", {
        method: "POST",
        body: JSON.stringify({ identifier: form.identifier.trim(), new_password: form.password }),
      });
      setIdentifier(form.identifier.trim());
      onNotice({ type: "success", message: payload.data?.message || t("success"), detail: "reset_password:success" });
      onClose();
    } catch (err) {
      setLocalError(errorNotice(err, "reset_password_failed").message);
      onNotice(errorNotice(err, "reset_password_failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <LoginDialog title={t("resetPasswordTitle")} body={t("resetPasswordBody")} onClose={onClose}>
      <form className="login-dialog-form" onSubmit={submit}>
        <label>
          <span>{t("identifier")}</span>
          <input value={form.identifier} onChange={(event) => setForm({ ...form, identifier: event.target.value })} />
        </label>
        <label>
          <span>{t("newPassword")}</span>
          <input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
        </label>
        <label>
          <span>{t("confirmPassword")}</span>
          <input type="password" value={form.confirm} onChange={(event) => setForm({ ...form, confirm: event.target.value })} />
        </label>
        {localError && <p className="error-text">{localError}</p>}
        <div className="dialog-actions">
          <button className="dialog-primary" disabled={busy}>
            {t("resetPasswordAction")}
          </button>
          <button type="button" className="dialog-secondary" onClick={onClose}>
            {t("cancel")}
          </button>
        </div>
      </form>
    </LoginDialog>
  );
}

function AccessRequestDialog({ onClose, onNotice }) {
  const { t } = usePreferences();
  const [form, setForm] = useState({ username: "", email: "", password: "", confirm: "" });
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setLocalError("");
    if (!looksLikeEmail(form.email)) {
      setLocalError(t("oauthEmailRequired"));
      return;
    }
    if (form.password.length < 4) {
      setLocalError(t("passwordTooShort"));
      return;
    }
    if (form.password !== form.confirm) {
      setLocalError(t("passwordMismatch"));
      return;
    }
    setBusy(true);
    try {
      const payload = await apiRequest("/api/auth/request-access/", {
        method: "POST",
        body: JSON.stringify({ username: form.username.trim(), email: form.email.trim(), password: form.password }),
      });
      onNotice({ type: "success", message: payload.data?.message || t("success"), detail: "request_access:success" });
      onClose();
    } catch (err) {
      setLocalError(errorNotice(err, "request_access_failed").message);
      onNotice(errorNotice(err, "request_access_failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <LoginDialog title={t("requestAccessTitle")} body={t("requestAccessBody")} onClose={onClose}>
      <form className="login-dialog-form" onSubmit={submit}>
        <label>
          <span>{t("username")}</span>
          <input value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} />
        </label>
        <label>
          <span>{t("email")}</span>
          <input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
        </label>
        <label>
          <span>{t("password")}</span>
          <input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
        </label>
        <label>
          <span>{t("confirmPassword")}</span>
          <input type="password" value={form.confirm} onChange={(event) => setForm({ ...form, confirm: event.target.value })} />
        </label>
        {localError && <p className="error-text">{localError}</p>}
        <div className="dialog-actions">
          <button className="dialog-primary" disabled={busy}>
            {t("submitRequest")}
          </button>
          <button type="button" className="dialog-secondary" onClick={onClose}>
            {t("cancel")}
          </button>
        </div>
      </form>
    </LoginDialog>
  );
}

function LoginDialog({ title, body, children, onClose }) {
  return (
    <div className="modal-backdrop">
      <section className="desktop-dialog login-dialog">
        <header>
          <h2>{title}</h2>
          <p>{body}</p>
          <button type="button" onClick={onClose}>
            x
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}

function errorNotice(err, fallbackCode) {
  const code = err?.payload?.code || fallbackCode;
  const loginMessages = {
    invalid_credentials: "Identifiant ou mot de passe incorrect. Verifiez vos informations puis reessayez.",
    missing_credentials: "Identifiant et mot de passe requis.",
    login_failed: "Connexion impossible. Verifiez vos informations puis reessayez.",
  };
  const message = loginMessages[code] || cleanLoginError(err?.message) || "Une erreur est survenue.";
  console.error("[UOR Web]", code, { status: err?.status, payload: err?.payload });
  return { type: "error", message };
}

function cleanLoginError(message) {
  const raw = String(message || "").trim();
  if (/^invalid credentials$/i.test(raw)) {
    return "Identifiant ou mot de passe incorrect. Verifiez vos informations puis reessayez.";
  }
  if (/^please enter credentials$/i.test(raw)) {
    return "Identifiant et mot de passe requis.";
  }
  return raw;
}

function oauthErrorMessage(code, language) {
  const fr = {
    oauth_not_configured: "Connexion sociale non configuree sur le serveur.",
    oauth_email_mismatch: "L'email du fournisseur ne correspond pas a l'email saisi.",
    oauth_local_account_missing: "Aucun compte local n'est associe a cet email.",
    oauth_state_invalid: "La session OAuth a expire. Reessayez.",
  };
  const en = {
    oauth_not_configured: "Social login is not configured on the server.",
    oauth_email_mismatch: "The provider email does not match the entered email.",
    oauth_local_account_missing: "No local account is linked to this email.",
    oauth_state_invalid: "The OAuth session expired. Try again.",
  };
  return (language === "EN" ? en : fr)[code] || (language === "EN" ? "OAuth login failed." : "Connexion OAuth impossible.");
}

function looksLikeEmail(value) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(value || "").trim());
}
