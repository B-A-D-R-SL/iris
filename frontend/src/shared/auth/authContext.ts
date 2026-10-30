// AI contribution: 50% or more AI-generated
import { createContext, useContext } from "react";

import type { CurrentUser } from "../../features/accounts/currentUser";

export interface AuthContextValue {
  user: CurrentUser | null | undefined;
  signIn: (email: string, password: string) => Promise<CurrentUser | "mfa_required">;
  verifyCode: (code: string) => Promise<CurrentUser>;
  retryProfile: () => Promise<CurrentUser>;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth requires AuthProvider");
  return value;
}
