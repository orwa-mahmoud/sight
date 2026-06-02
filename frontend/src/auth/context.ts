import { createContext } from "react";

import type * as authApi from "./api";
import type { MeResponse } from "./types";

export interface AuthContextValue {
  user: MeResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (req: Parameters<typeof authApi.register>[0]) => Promise<void>;
  /** Re-fetch the current user (e.g. after joining a tenant via an invite). */
  refresh: () => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
