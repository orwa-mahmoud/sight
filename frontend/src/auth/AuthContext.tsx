import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { setUnauthorizedHandler } from "@core/api/client";
import * as authApi from "./api";
import { AuthContext, type AuthContextValue } from "./context";
import type { MeResponse } from "./types";

export function AuthProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const loadCurrentUser = useCallback(async () => {
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      setUser(null);
    }
  }, []);

  // Bootstrap: the httpOnly cookie (if present) is sent automatically. A 401
  // here simply means "not logged in" — not an error.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await authApi.me();
        if (!cancelled) setUser(me);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Reset auth state if any request comes back 401 (e.g. the session expired).
  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    return () => setUnauthorizedHandler(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (email, password) => {
        await authApi.login(email, password);
        await loadCurrentUser();
      },
      register: async (req) => {
        await authApi.register(req);
        await loadCurrentUser();
      },
      refresh: loadCurrentUser,
      logout: () => {
        setUser(null);
        authApi.logout().catch(() => undefined);
      },
    }),
    [user, loading, loadCurrentUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
