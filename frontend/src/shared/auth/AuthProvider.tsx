// AI contribution: 50% or more AI-generated
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import {
  CURRENT_USER_QUERY_KEY,
  fetchCurrentUser,
  useCurrentUser,
} from "../../features/accounts/currentUser";
import { AuthError, loginWithCode, loginWithPassword, logout } from "./api";
import { AuthContext, type AuthContextValue } from "./authContext";

const AUTH_EVENT_KEY = "iris:auth-change";

/** Reuse the existing /api/me/ query for every screen and react to other tabs. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { i18n } = useTranslation();
  const { data: user } = useCurrentUser();

  useEffect(() => {
    function onStorage(event: StorageEvent) {
      if (event.key !== AUTH_EVENT_KEY) return;
      if (event.newValue?.startsWith("signed-out:")) {
        void queryClient.cancelQueries({ queryKey: CURRENT_USER_QUERY_KEY }).then(() => {
          queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null);
        });
      } else if (event.newValue?.startsWith("signed-in:")) {
        void queryClient.invalidateQueries({ queryKey: CURRENT_USER_QUERY_KEY });
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [queryClient]);

  function notifyTabs(state: "signed-in" | "signed-out") {
    try {
      // Only a state-change marker is shared; no personal data or credentials.
      localStorage.setItem(AUTH_EVENT_KEY, `${state}:${crypto.randomUUID()}`);
    } catch {
      // The backend still revokes the session if browser storage is unavailable.
    }
  }

  async function loadSignedInUser(): Promise<NonNullable<AuthContextValue["user"]>> {
    let current: AuthContextValue["user"];
    try {
      await queryClient.invalidateQueries({
        queryKey: CURRENT_USER_QUERY_KEY,
        refetchType: "none",
      });
      current = await queryClient.fetchQuery({
        queryKey: CURRENT_USER_QUERY_KEY,
        queryFn: fetchCurrentUser,
        staleTime: 0,
      });
    } catch {
      throw new AuthError("profile_unavailable");
    }
    if (!current) throw new AuthError("profile_unavailable");
    notifyTabs("signed-in");
    return current;
  }

  const language = i18n.resolvedLanguage ?? "fr";
  const value: AuthContextValue = {
    user,
    async signIn(email, password) {
      const result = await loginWithPassword(email, password, language);
      return result === "mfa_required" ? result : loadSignedInUser();
    },
    async verifyCode(code) {
      await loginWithCode(code, language);
      return loadSignedInUser();
    },
    retryProfile: loadSignedInUser,
    async signOut() {
      await logout(language);
      await queryClient.cancelQueries({ queryKey: CURRENT_USER_QUERY_KEY });
      queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null);
      notifyTabs("signed-out");
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
