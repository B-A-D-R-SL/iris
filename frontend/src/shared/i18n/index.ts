// AI contribution: 50% or more AI-generated
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import { DEFAULT_LANGUAGE, rememberLanguage, storedLanguage } from "./languagePreference";
import { resources } from "./resources";

// Keep the HTML document language synchronized with i18next, and remember the
// choice for the next visit (US-08).
i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
  rememberLanguage(lng);
});

void i18n.use(initReactI18next).init({
  resources,
  lng: storedLanguage(),
  fallbackLng: DEFAULT_LANGUAGE,
  supportedLngs: ["fr", "en"],
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
