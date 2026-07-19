import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./auth-context";

type Props = {
  allowedRoles?: Array<"admin" | "editor" | "viewer">;
};

export function RequireAuth({ allowedRoles }: Props) {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
