import { createContext, useContext, useMemo, useState } from "react";

import { apiRequest } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("uor_token") || "");
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("uor_user");
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      localStorage.removeItem("uor_token");
      localStorage.removeItem("uor_user");
      return null;
    }
  });

  async function login(identifier, password) {
    const payload = await apiRequest("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify({ identifier, password }),
    });
    const data = payload.data;
    localStorage.setItem("uor_token", data.token);
    localStorage.setItem("uor_user", JSON.stringify(data.user));
    setToken(data.token);
    setUser(data.user);
    return data.user;
  }

  function acceptSession(data) {
    if (!data?.token || !data?.user) {
      throw new Error("Session invalide recue du serveur.");
    }
    localStorage.setItem("uor_token", data.token);
    localStorage.setItem("uor_user", JSON.stringify(data.user));
    setToken(data.token);
    setUser(data.user);
    return data.user;
  }

  function logout() {
    localStorage.removeItem("uor_token");
    localStorage.removeItem("uor_user");
    setToken("");
    setUser(null);
  }

  const value = useMemo(
    () => ({ isAuthenticated: Boolean(token), token, user, login, acceptSession, logout }),
    [token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
