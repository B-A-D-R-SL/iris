// AI contribution: 50% or more AI-generated
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import fr from "./fr.json";
import en from "./en.json";

void i18n.use(initReactI18next).init({
  resources: {
    fr: { translation: fr },
    en: { translation: en },
  },
  lng: "fr",
  fallbackLng: "fr",
  supportedLngs: ["fr", "en"],
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
