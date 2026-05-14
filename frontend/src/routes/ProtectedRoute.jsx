import { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../state/AuthContext.jsx";
import { saveLastAppLocation } from "./lastLocation.js";

export function ProtectedRoute({ children }) {
  const auth = useAuth();
  const location = useLocation();

  useEffect(() => {
    if (!auth.isAuthenticated) {
      saveLastAppLocation(location);
    }
  }, [auth.isAuthenticated, location]);

  if (!auth.isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}
