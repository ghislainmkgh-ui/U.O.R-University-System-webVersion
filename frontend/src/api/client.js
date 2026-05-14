const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("uor_token");
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });
  } catch (err) {
    throw new ApiError(
      `Backend indisponible sur ${API_BASE_URL}. Lancez Django puis rechargez la page.`,
      0,
      { cause: err.message },
    );
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const rawMessage = typeof payload === "object" ? payload.error || "Erreur API" : payload || "Erreur API";
    const message = publicApiMessage(rawMessage, payload, response.status);
    throw new ApiError(message, response.status, payload);
  }

  return payload;
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}

export async function downloadApiFile(path, filename) {
  const token = localStorage.getItem("uor_token");
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch (err) {
    throw new ApiError(
      `Backend indisponible sur ${API_BASE_URL}. Lancez Django puis rechargez la page.`,
      0,
      { cause: err.message },
    );
  }

  if (!response.ok) {
    throw new ApiError("Telechargement impossible", response.status, null);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function publicApiMessage(message, payload, status) {
  const raw = String(message || "").trim();
  const code = typeof payload === "object" && payload ? payload.code : "";
  const technicalKey = technicalErrorKey(raw);
  const publicCodeMessages = {
    invalid_credentials: "Identifiant ou mot de passe incorrect. Verifiez vos informations puis reessayez.",
    missing_credentials: "Identifiant et mot de passe requis.",
  };

  if (publicCodeMessages[code]) {
    return publicCodeMessages[code];
  }

  if (/^invalid credentials$/i.test(raw) || /^please enter credentials$/i.test(raw)) {
    return fallbackMessage("invalid_credentials", status);
  }

  const technicalMessages = {
    OVERPAYMENT: "Le paiement depasse le montant total des frais academiques. Verifiez le reste a payer avant d'enregistrer.",
    NO_ACTIVE_FEES: "Aucun frais academique actif n'est configure pour cette promotion.",
    NO_FINANCE_PROFILE: "Le profil financier de cet etudiant est introuvable.",
    NO_PROMOTION_DATA: "Les informations de promotion de cet etudiant sont introuvables.",
    PAYMENT_EXCEPTION: "Paiement impossible pour le moment. Veuillez reessayer.",
    NO_ACCESS_CODE: "Aucun code d'acces n'existe encore pour cet etudiant.",
    ACCESS_CODE_EXPIRED: "Le dernier code d'acces est expire. Enregistrez un nouveau paiement valide ou regenerez un code.",
    INVALID_ACCESS_CODE: "Le dernier code d'acces est invalide. Generez un nouveau code pour cet etudiant.",
    ACCESS_CODE_NOTIFICATION_FAILED: "Le code existe, mais l'envoi a echoue. Verifiez l'email ou le numero WhatsApp.",
    ACCESS_CODE_RESEND_EXCEPTION: "Le code n'a pas pu etre envoye pour le moment. Veuillez reessayer.",
  };

  if (technicalKey) {
    return technicalMessages[technicalKey] || fallbackMessage(code, status);
  }

  if (looksTechnical(raw)) {
    return fallbackMessage(code, status);
  }

  return raw || fallbackMessage(code, status);
}

function technicalErrorKey(message) {
  return String(message || "").match(/^\s*([A-Z][A-Z0-9_]+)\s*:/)?.[1] || "";
}

function looksTechnical(message) {
  const raw = String(message || "");
  return (
    Boolean(technicalErrorKey(raw)) ||
    raw.includes("student_id=") ||
    raw.includes("Traceback") ||
    raw.includes("Exception") ||
    /\b(ModuleNotFoundError|OperationalError|IntegrityError|TypeError|ValueError|KeyError)\b/.test(raw) ||
    raw.includes("mysql.connector") ||
    raw.includes('File "') ||
    /[a-zA-Z_]+=[^;]+;/.test(raw) ||
    /[A-Za-z]:\\/.test(raw)
  );
}

function fallbackMessage(code, status) {
  const messages = {
    payment_failed: "Paiement refuse. Verifiez le montant et la situation financiere de l'etudiant.",
    access_code_resend_failed: "Le code n'a pas pu etre envoye. Verifiez les contacts de l'etudiant et reessayez.",
    invalid_credentials: "Identifiant ou mot de passe incorrect. Verifiez vos informations puis reessayez.",
    missing_credentials: "Identifiant et mot de passe requis.",
    invalid_token: "Votre session n'est plus valide. Connectez-vous a nouveau.",
    token_expired: "Votre session a expire. Connectez-vous a nouveau.",
    auth_required: "Connexion requise.",
  };
  if (messages[code]) return messages[code];
  if (status === 0) return "Backend indisponible. Lancez Django puis rechargez la page.";
  if (status === 401) return "Connexion requise.";
  if (status === 403) return "Acces refuse.";
  return "Une erreur est survenue. Veuillez reessayer.";
}
