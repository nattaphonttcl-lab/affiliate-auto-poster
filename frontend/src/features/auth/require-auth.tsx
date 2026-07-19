import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./auth-context";

type Props = {
  allowedRoles?: Array<"admin" | "editor" | "viewer">;
  allowPasswordChange?: boolean;
};

export function RequireAuth({ allowedRoles, allowPasswordChange = false }: Props) {
  const { isAuthenticated, user, mustChangePassword } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (mustChangePassword && !allowPasswordChange) {
    return <Navigate to="/change-password" replace />;
  }

  if (!mustChangePassword && allowPasswordChange) {
    return <Navigate to="/dashboard" replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
