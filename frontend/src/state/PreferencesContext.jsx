import { createContext, useContext, useEffect, useMemo, useState } from "react";

const PreferencesContext = createContext(null);

const dictionaries = {
  FR: {
    appTitle: "TABLEAU DE BORD ADMIN",
    compact: "Compact",
    full: "Complet",
    modeCompact: "Mode: Compact",
    modeFull: "Mode: Complet",
    logout: "Deconnexion",
    dashboard: "Tableau de Bord",
    students: "Etudiants",
    accessRequests: "Demandes d'acces",
    academics: "Donnees Academiques",
    finance: "Finances",
    academicYears: "Annees Acad.",
    transfers: "Transferts",
    accessLogs: "Logs d'Acces",
    reports: "Rapports",
    language: "Langue",
    lightTheme: "Theme clair",
    darkTheme: "Theme sombre",
    loading: "Chargement...",
    displayError: "Erreur d'affichage",
    displayErrorBody: "Une erreur a empeche le chargement de l'interface.",
    resetSession: "Reinitialiser la session",
    loginTitle: "Connexion securisee",
    loginSubtitle: "Accedez a l'espace U.O.R avec votre compte autorise.",
    visualBadge: "Acces securise",
    visualWelcome: "Bienvenue.",
    identifier: "Email / Identifiant",
    identifierPlaceholder: "ex: admin@uor.cd ou UOR UNIVERSITY",
    password: "Mot de passe",
    newPassword: "Nouveau mot de passe",
    confirmPassword: "Confirmer le mot de passe",
    rememberMe: "Se souvenir de moi",
    forgotPassword: "Mot de passe oublie ?",
    signIn: "Se connecter",
    signingIn: "Connexion...",
    createAccount: "Creer un compte",
    or: "ou",
    continueGoogle: "Continuer avec Google",
    continueGithub: "Continuer avec GitHub",
    requestAccessTitle: "Demande d'acces administrateur",
    requestAccessBody: "Votre demande sera envoyee au super administrateur pour validation.",
    username: "Nom utilisateur",
    email: "Email",
    submitRequest: "Envoyer la demande",
    resetPasswordTitle: "Reinitialiser le mot de passe",
    resetPasswordBody: "Saisissez votre identifiant et choisissez un nouveau mot de passe.",
    resetPasswordAction: "Reinitialiser",
    cancel: "Annuler",
    close: "Fermer",
    success: "Succes",
    passwordMismatch: "Les deux mots de passe ne correspondent pas.",
    passwordTooShort: "Le mot de passe doit contenir au moins 4 caracteres.",
    missingCredentials: "Veuillez saisir votre identifiant et votre mot de passe.",
    oauthEmailRequired: "Saisissez d'abord une adresse email valide dans le champ Email / Identifiant.",
    oauthStarting: "Redirection vers le fournisseur...",
    oauthSuccess: "Connexion OAuth validee.",
    backendUnavailable: "Backend indisponible. Lancez Django puis rechargez la page.",
  },
  EN: {
    appTitle: "ADMIN DASHBOARD",
    compact: "Compact",
    full: "Full",
    modeCompact: "Mode: Compact",
    modeFull: "Mode: Full",
    logout: "Logout",
    dashboard: "Dashboard",
    students: "Students",
    accessRequests: "Access Requests",
    academics: "Academic Data",
    finance: "Finance",
    academicYears: "Academic Years",
    transfers: "Transfers",
    accessLogs: "Access Logs",
    reports: "Reports",
    language: "Language",
    lightTheme: "Light theme",
    darkTheme: "Dark theme",
    loading: "Loading...",
    displayError: "Display error",
    displayErrorBody: "An error prevented the interface from loading.",
    resetSession: "Reset session",
    loginTitle: "Secure sign in",
    loginSubtitle: "Access the U.O.R workspace with your authorized account.",
    visualBadge: "Secure access",
    visualWelcome: "Welcome.",
    identifier: "Email / Username",
    identifierPlaceholder: "e.g. admin@uor.cd or UOR UNIVERSITY",
    password: "Password",
    newPassword: "New password",
    confirmPassword: "Confirm password",
    rememberMe: "Remember me",
    forgotPassword: "Forgot password?",
    signIn: "Sign in",
    signingIn: "Signing in...",
    createAccount: "Create account",
    or: "or",
    continueGoogle: "Continue with Google",
    continueGithub: "Continue with GitHub",
    requestAccessTitle: "Administrator access request",
    requestAccessBody: "Your request will be sent to the super administrator for approval.",
    username: "Username",
    email: "Email",
    submitRequest: "Submit request",
    resetPasswordTitle: "Reset password",
    resetPasswordBody: "Enter your identifier and choose a new password.",
    resetPasswordAction: "Reset password",
    cancel: "Cancel",
    close: "Close",
    success: "Success",
    passwordMismatch: "The two passwords do not match.",
    passwordTooShort: "The password must contain at least 4 characters.",
    missingCredentials: "Please enter your identifier and password.",
    oauthEmailRequired: "Enter a valid email address in Email / Username first.",
    oauthStarting: "Redirecting to provider...",
    oauthSuccess: "OAuth sign in verified.",
    backendUnavailable: "Backend unavailable. Start Django and reload the page.",
  },
};

const literalKeys = new Map([
  ["Tableau de Bord", "dashboard"],
  ["Etudiants", "students"],
  ["Demandes d'acces", "accessRequests"],
  ["Donnees Academiques", "academics"],
  ["Finances", "finance"],
  ["Annees Acad.", "academicYears"],
  ["Transferts", "transfers"],
  ["Logs d'Acces", "accessLogs"],
  ["Rapports", "reports"],
  ["Chargement...", "loading"],
  ["Erreur d'affichage", "displayError"],
  ["Reinitialiser la session", "resetSession"],
]);

const phrasePairs = [
  ["Tableau de Bord", "Dashboard"],
  ["Etudiants", "Students"],
  ["Demandes d'acces", "Access Requests"],
  ["Donnees Academiques", "Academic Data"],
  ["Finances", "Finance"],
  ["Annees Acad.", "Academic Years"],
  ["Transferts", "Transfers"],
  ["Logs d'Acces", "Access Logs"],
  ["Rapports", "Reports"],
  ["Gestion Financiere", "Financial Management"],
  ["Suivi des paiements et seuils", "Payment and threshold tracking"],
  ["Historique d'Acces", "Access History"],
  ["Suivi des tentatives d'acces", "Access attempt tracking"],
  ["Notes, cours et documents par etudiant", "Grades, courses and documents by student"],
  ["Transferts Inter-Universitaires", "Inter-University Transfers"],
  ["Transferts sortants, demandes entrantes et historique", "Outgoing transfers, incoming requests and history"],
  ["Exports et vues de controle", "Exports and control views"],
  ["Connexion securisee", "Secure sign in"],
  ["Acces securise", "Secure access"],
  ["Bienvenue.", "Welcome."],
  ["Se connecter", "Sign in"],
  ["Creer un compte", "Create account"],
  ["Mot de passe oublie ?", "Forgot password?"],
  ["Se souvenir de moi", "Remember me"],
  ["Email / Identifiant", "Email / Username"],
  ["Mot de passe", "Password"],
  ["Actualiser", "Refresh"],
  ["Ajouter", "Add"],
  ["Supprimer", "Delete"],
  ["Fermer", "Close"],
  ["Annuler", "Cancel"],
  ["En attente", "Pending"],
  ["Admins approuves", "Approved admins"],
  ["Administrateurs", "Administrators"],
  ["Demandes en attente", "Pending requests"],
  ["Aucune donnee", "No data"],
  ["Aucun etudiant trouve.", "No student found."],
  ["Aucune demande d'acces en attente.", "No pending access request."],
  ["Aucun administrateur approuve.", "No approved administrator."],
  ["Tous", "All"],
  ["Statut", "Status"],
  ["Action", "Action"],
  ["Actions", "Actions"],
  ["Date", "Date"],
  ["Email", "Email"],
  ["Utilisateur", "User"],
  ["Role", "Role"],
  ["Etat", "State"],
  ["Actif", "Active"],
  ["Inactif", "Inactive"],
];

const phraseMaps = {
  FR: new Map(phrasePairs.map(([fr, en]) => [en, fr])),
  EN: new Map(phrasePairs.map(([fr, en]) => [fr, en])),
};

export function PreferencesProvider({ children }) {
  const [language, setLanguage] = useState(() => localStorage.getItem("uor_language") || "FR");
  const [theme, setTheme] = useState(() => localStorage.getItem("uor_theme") || "light");

  useEffect(() => {
    const safeLanguage = language === "EN" ? "EN" : "FR";
    localStorage.setItem("uor_language", safeLanguage);
    document.documentElement.lang = safeLanguage.toLowerCase();
  }, [language]);

  useEffect(() => {
    const safeTheme = theme === "dark" ? "dark" : "light";
    localStorage.setItem("uor_theme", safeTheme);
    document.documentElement.dataset.theme = safeTheme;
  }, [theme]);

  useEffect(() => {
    const translateNode = (node) => {
      if (!node || node.nodeType !== Node.TEXT_NODE) return;
      const raw = node.nodeValue || "";
      const trimmed = raw.trim();
      if (!trimmed) return;
      const translated = phraseMaps[language]?.get(trimmed);
      if (!translated) return;
      node.nodeValue = raw.replace(trimmed, translated);
    };

    const translateTree = (root) => {
      if (!root) return;
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let node = walker.nextNode();
      while (node) {
        translateNode(node);
        node = walker.nextNode();
      }
    };

    translateTree(document.body);
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.TEXT_NODE) {
            translateNode(node);
          } else {
            translateTree(node);
          }
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [language]);

  const value = useMemo(() => {
    const safeLanguage = language === "EN" ? "EN" : "FR";
    const dictionary = dictionaries[safeLanguage];
    const t = (key, fallback = "") => dictionary[key] || dictionaries.FR[key] || fallback || key;
    const tx = (text) => {
      const key = literalKeys.get(text);
      return key ? t(key, text) : text;
    };
    return {
      language: safeLanguage,
      theme: theme === "dark" ? "dark" : "light",
      setLanguage,
      setTheme,
      toggleTheme: () => setTheme((current) => (current === "dark" ? "light" : "dark")),
      t,
      tx,
    };
  }, [language, theme]);

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences() {
  return useContext(PreferencesContext);
}
