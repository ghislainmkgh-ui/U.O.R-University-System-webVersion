import { Navigate } from "react-router-dom";

import { canAccessView } from "../auth/permissions.js";
import { useAuth } from "../state/AuthContext.jsx";

export function AppNavigationGuard({ children, viewKey }) {
  const auth = useAuth();

  if (viewKey && !canAccessView(auth.user?.role, viewKey)) {
    return <Navigate to="/" replace />;
  }

  return children;
}
