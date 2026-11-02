// AI contribution: 50% or more AI-generated
import { type QueryClient, useQueryClient } from "@tanstack/react-query";
import { useEffect, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import {
  CURRENT_USER_QUERY_KEY,
  fetchCurrentUser,
  useCurrentUser,
} from "../../features/accounts/currentUser";
import { logger } from "../logger";
import { AuthError, loginWithCode, loginWithPassword, logout } from "./api";
import { AuthContext, type AuthContextValue } from "./authContext";

const AUTH_EVENT_KEY = "iris:auth-change";

/** Cancel requests and drop data that belongs to a previous user. */
async function clearCachedQueries(queryClient: QueryClient) {
  await queryClient.cancelQueries();
  queryClient.removeQueries({
    predicate: (query) => query.queryKey[0] !== CURRENT_USER_QUERY_KEY[0],
  });
}

/** Drop responses cached for the previous user and mark the session as signed out. */
async function clearSessionData(queryClient: QueryClient) {
  await clearCachedQueries(queryClient);
  queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null);
}

/** Listen for session changes and notify other tabs without sharing account data. */
function useAuthTabSync(queryClient: QueryClient) {
  useEffect(() => {
    function onStorage(event: StorageEvent) {
      if (event.key !== AUTH_EVENT_KEY) return;
      if (event.newValue?.startsWith("signed-out:")) {
        void clearSessionData(queryClient);
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
      logger.warning("auth_tab_sync_unavailable");
    }
  }

  return notifyTabs;
}

async function loadSignedInUser(
  queryClient: QueryClient,
  notifyTabs: (state: "signed-in" | "signed-out") => void,
): Promise<NonNullable<AuthContextValue["user"]>> {
  let current: AuthContextValue["user"];
  try {
    await clearCachedQueries(queryClient);
    await queryClient.invalidateQueries({ queryKey: CURRENT_USER_QUERY_KEY, refetchType: "none" });
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

/** Reuse the existing /api/me/ query for every screen and react to other tabs. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { i18n } = useTranslation();
  const { data: user } = useCurrentUser();
  const notifyTabs = useAuthTabSync(queryClient);
  const loadUser = () => loadSignedInUser(queryClient, notifyTabs);

  const language = i18n.resolvedLanguage ?? "fr";
  const value: AuthContextValue = {
    user,
    async signIn(email, password) {
      const result = await loginWithPassword(email, password, language);
      return result === "mfa_required" ? result : loadUser();
    },
    async verifyCode(code) {
      await loginWithCode(code, language);
      return loadUser();
    },
    retryProfile: loadUser,
    async signOut() {
      await logout(language);
      await clearSessionData(queryClient);
      notifyTabs("signed-out");
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
