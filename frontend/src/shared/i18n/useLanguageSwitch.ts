// AI contribution: 50% or more AI-generated
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  CURRENT_USER_QUERY_KEY,
  type CurrentUser,
  saveLanguage,
  useCurrentUser,
} from "../auth/currentUser";
import { logger } from "../logger";
import type { Language } from "./languagePreference";

/**
 * Saves run one after another, so quick switches reach the server in the order
 * they were chosen and the last choice is the one the account keeps.
 */
let saving: Promise<void> = Promise.resolve();

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

  /** False once the account that chose the language signed out or another signed in. */
  function stillSignedIn(accountId: string) {
    return queryClient.getQueryData<CurrentUser | null>(CURRENT_USER_QUERY_KEY)?.id === accountId;
  }

  async function save(accountId: string, language: Language) {
    // A save still queued when the account changed is dropped: sent now, it
    // would change the language of whoever is signed in instead.
    if (!stillSignedIn(accountId)) return;
    try {
      const saved = await saveLanguage(language);
      if (stillSignedIn(accountId)) {
        queryClient.setQueryData(CURRENT_USER_QUERY_KEY, saved);
      }
    } catch {
      logger.warning("language_save_failed");
    }
  }

  async function switchLanguage() {
    await i18n.changeLanguage(next);
    logger.info("language_changed");
    if (!user) return;
    const accountId = user.id;
    saving = saving.then(() => save(accountId, next));
    await saving;
  }

  return { next, switchLanguage };
}
