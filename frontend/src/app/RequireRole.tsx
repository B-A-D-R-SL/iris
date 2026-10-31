// AI contribution: 50% or more AI-generated
import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router";

import { useCurrentUser, type Role } from "../features/accounts/currentUser";
import { ErrorState, LoadingState } from "../shared/ui";
import { homePathFor } from "./navigation";

interface RequireRoleProps {
  roles: readonly Role[];
  /** Without children it guards the nested routes (<Outlet />). */
  children?: ReactNode;
}

/**
 * Only shows a screen to the roles allowed to use it: signed-out visitors go to
 * sign-in, other roles go to their own home. This is for the interface only;
 * the API refuses the same requests on the server.
 */
export function RequireRole({ roles, children }: RequireRoleProps) {
  const { data: user, isPending, isError, refetch } = useCurrentUser();
  const location = useLocation();

  if (isPending) return <LoadingState />;
  if (isError) return <ErrorState onRetry={() => void refetch()} />;
  if (!user) return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  if (!roles.includes(user.role)) return <Navigate to={homePathFor(user.role)} replace />;
  return children ?? <Outlet />;
}
