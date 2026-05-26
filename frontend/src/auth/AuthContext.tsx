import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { clearToken, getToken, setToken } from "../core/api/client";
import * as authApi from "./api";
import { AuthContext, type AuthContextValue } from "./context";
import type { MeResponse } from "./types";

export function AuthProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const loadCurrentUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Bootstrap effect: load the current user once on mount. setUser is
    // called only after the awaited promise resolves, so the lint rule
    // about synchronous setState-in-effect doesn't apply here.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadCurrentUser();
  }, [loadCurrentUser]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (email, password) => {
        const token = await authApi.login(email, password);
        setToken(token.access_token);
        await loadCurrentUser();
      },
      register: async (req) => {
        const token = await authApi.register(req);
        setToken(token.access_token);
        await loadCurrentUser();
      },
      logout: () => {
        clearToken();
        setUser(null);
        fetch("/api/v1/auth/logout", { method: "POST", credentials: "include" }).catch(() => {});
      },
    }),
    [user, loading, loadCurrentUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
