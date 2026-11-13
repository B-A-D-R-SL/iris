// AI contribution: 50% or more AI-generated
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import { resources } from "./resources";

// Keep the HTML document language synchronized with i18next.
i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
});

void i18n.use(initReactI18next).init({
  resources,
  lng: "fr",
  fallbackLng: "fr",
  supportedLngs: ["fr", "en"],
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
