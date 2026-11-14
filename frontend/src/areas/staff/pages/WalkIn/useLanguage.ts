// AI contribution: 50% or more AI-generated
import { useTranslation } from "react-i18next";

/** The two interface languages, for API headers and number and date formats. */
export function useLanguage(): "fr" | "en" {
  const { i18n } = useTranslation();
  return i18n.resolvedLanguage === "en" ? "en" : "fr";
}
