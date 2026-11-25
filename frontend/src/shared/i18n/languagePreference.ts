// AI contribution: 50% or more AI-generated
/**
 * The interface language (US-08). French by default; a visitor's choice is kept
 * in this browser so it survives a reload, and a signed-in user's choice is also
 * saved on their account (PATCH /api/me/), which wins after sign-in.
 */
import { logger } from "../logger";

export type Language = "fr" | "en";

export const DEFAULT_LANGUAGE: Language = "fr";
const STORAGE_KEY = "iris:language";

export function isLanguage(value: unknown): value is Language {
  return value === "fr" || value === "en";
}

/** The language this browser last chose, or French. Storage can be blocked. */
export function storedLanguage(): Language {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return isLanguage(value) ? value : DEFAULT_LANGUAGE;
  } catch {
    logger.warning("language_storage_unavailable");
    return DEFAULT_LANGUAGE;
  }
}

/** Keep the choice for the next visit; only "fr" or "en" is stored. */
export function rememberLanguage(language: string): void {
  if (!isLanguage(language)) return;
  try {
    localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Blocked storage only means the next visit starts in French.
    logger.warning("language_storage_unavailable");
  }
}
