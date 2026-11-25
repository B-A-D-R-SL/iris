// AI contribution: 50% or more AI-generated
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { CURRENT_USER_QUERY_KEY, saveLanguage, useCurrentUser } from "../auth/currentUser";
import { logger } from "../logger";
import type { Language } from "./languagePreference";

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
    await i18n.changeLanguage(next);
    logger.info("language_changed");
    if (!user) return;
    try {
      queryClient.setQueryData(CURRENT_USER_QUERY_KEY, await saveLanguage(next));
    } catch {
      logger.warning("language_save_failed");
    }
  }

  return { next, switchLanguage };
}
