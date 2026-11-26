// AI contribution: 50% or more AI-generated
import { type QueryClient, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  CURRENT_USER_QUERY_KEY,
  type CurrentUser,
  fetchCurrentUser,
  LanguageSaveError,
  saveLanguage,
  useCurrentUser,
} from "../auth/currentUser";
import { logger } from "../logger";
import type { Language } from "./languagePreference";

/**
 * Saves run one after another, so quick switches reach the server in the order
 * they were chosen and the last choice is the one the account keeps. The queue
 * belongs to the app's QueryClient (the cache holding the account), so separate
 * clients, such as one per test, never wait on each other; a save that gets no
 * answer gives up after a timeout (`saveLanguage`), so it cannot hold the queue.
 */
const saveQueues = new WeakMap<QueryClient, Promise<void>>();

function enqueue(queryClient: QueryClient, save: () => Promise<void>): Promise<void> {
  const queued = (saveQueues.get(queryClient) ?? Promise.resolve()).then(save);
  saveQueues.set(queryClient, queued);
  return queued;
}

/** False once the account that chose the language signed out or another signed in. */
function stillSignedIn(queryClient: QueryClient, accountId: string): boolean {
  return queryClient.getQueryData<CurrentUser | null>(CURRENT_USER_QUERY_KEY)?.id === accountId;
}

/** The signed-in account, waiting for /api/me/ if it is still loading; null if none. */
async function signedInAccount(
  queryClient: QueryClient,
  user: CurrentUser | null | undefined,
): Promise<CurrentUser | null> {
  if (user !== undefined) return user;
  try {
    return await queryClient.ensureQueryData({
      queryKey: CURRENT_USER_QUERY_KEY,
      queryFn: fetchCurrentUser,
    });
  } catch {
    // Not a sign-out: the account could not be read, so the choice stays in
    // this browser only, and the failure is logged.
    logger.warning("language_account_unavailable");
    return null;
  }
}

/**
 * Saves `language` on the account `accountId`. A save still queued when the
 * account changed is dropped: sent now, it would change the language of
 * whoever is signed in instead. After a failed save the account is read again,
 * so the cache holds what the server last confirmed (an earlier save in the
 * queue may have succeeded); the screen keeps the chosen language.
 */
async function save(queryClient: QueryClient, accountId: string, language: Language) {
  if (!stillSignedIn(queryClient, accountId)) return;
  try {
    const account = await saveLanguage(language, accountId);
    if (stillSignedIn(queryClient, accountId)) {
      queryClient.setQueryData(CURRENT_USER_QUERY_KEY, account);
    }
  } catch (error) {
    if (stillSignedIn(queryClient, accountId)) {
      void queryClient.invalidateQueries({ queryKey: CURRENT_USER_QUERY_KEY });
    }
    if (error instanceof LanguageSaveError) {
      logger.warning("language_save_failed", { statusCode: error.statusCode });
    } else {
      logger.warning("language_save_response_invalid");
    }
  }
}

/**
 * The other language and the action that switches to it (US-08). The screen
 * changes at once; for a signed-in user the choice is also saved on the account,
 * so the next sign-in and every email use it. If saving fails the screen keeps
 * the new language and the account keeps the old one.
 */
export function useLanguageSwitch() {
  const { i18n } = useTranslation();
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const next: Language = i18n.resolvedLanguage === "en" ? "fr" : "en";

  async function switchLanguage() {
    const loading = user === undefined;
    await i18n.changeLanguage(next);
    logger.info("language_changed");
    const account = await signedInAccount(queryClient, user);
    if (!account) return;
    if (loading) {
      // The account loaded after this choice, so the choice wins over the
      // language saved on it. Caching it with the choice keeps AuthProvider's
      // sign-in language from switching the screen back.
      queryClient.setQueryData(CURRENT_USER_QUERY_KEY, { ...account, language: next });
      if (i18n.resolvedLanguage !== next) await i18n.changeLanguage(next);
    }
    await enqueue(queryClient, () => save(queryClient, account.id, next));
  }

  return { next, switchLanguage };
}
