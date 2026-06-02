import { Center, Loader } from "@mantine/core";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "@auth/useAuth";

/**
 * Route guard for tenant-owner-only pages (settings, team). Assumes it renders
 * inside `RequireAuth`; redirects non-owners (STAFF) to the dashboard home.
 */
export function RequireOwner({ children }: Readonly<{ children: ReactNode }>) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Center mih="100vh">
        <Loader />
      </Center>
    );
  }
  if (user?.tenant.role !== "owner") {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
