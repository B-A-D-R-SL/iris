import { describe, expect, it } from "vitest";
import { createInstance } from "i18next";

import en from "../shared/i18n/en.json";
import fr from "../shared/i18n/fr.json";

type TranslationTree = { [key: string]: string | TranslationTree };

function flatten(tree: TranslationTree, prefix = ""): Record<string, string> {
  const result: Record<string, string> = {};

  for (const [key, value] of Object.entries(tree)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "string") {
      result[path] = value;
    } else {
      Object.assign(result, flatten(value, path));
    }
  }

  return result;
}

const english = flatten(en);
const french = flatten(fr);
const originalKeys = [
  "title",
  "description",
  "language",
  "status",
  "backend.label",
  "backend.checking",
  "backend.online",
  "backend.offline",
];

// Original homepage keys predate the area.screen.element convention.
const legacyKeys = new Set(originalKeys);

describe("SET-13 translations", () => {
  it("has exactly the same keys in French and English", () => {
    expect(Object.keys(french).sort()).toEqual(Object.keys(english).sort());
  });

  it("has no empty translations", () => {
    for (const [language, entries] of [
      ["en", english],
      ["fr", french],
    ] as const) {
      for (const [key, value] of Object.entries(entries)) {
        expect(value.trim(), `${language}: ${key}`).not.toBe("");
      }
    }
  });

  it("uses area.screen.element for new keys", () => {
    const segment = /^[a-z][a-zA-Z0-9]*$/;
    for (const key of Object.keys(english)) {
      if (legacyKeys.has(key)) continue;
      const parts = key.split(".");
      expect(parts.length, key).toBeGreaterThanOrEqual(3);
      expect(
        parts.every((part) => segment.test(part)),
        key,
      ).toBe(true);
    }
  });

  it("preserves the original homepage and backend translations", () => {
    expect(Object.fromEntries(originalKeys.map((key) => [key, english[key]]))).toEqual({
      title: "Welcome to Iris",
      description:
        "A solidarity redistribution platform connecting communities and making resource sharing easier.",
      language: "Français",
      status: "Project setup in progress",
      "backend.label": "Server status",
      "backend.checking": "Checking...",
      "backend.online": "Connected",
      "backend.offline": "Unavailable",
    });
    expect(Object.fromEntries(originalKeys.map((key) => [key, french[key]]))).toEqual({
      title: "Bienvenue sur Iris",
      description:
        "Une plateforme de redistribution solidaire pour connecter les communautés et faciliter le partage des ressources.",
      language: "English",
      status: "Configuration du projet en cours",
      "backend.label": "État du serveur",
      "backend.checking": "Vérification...",
      "backend.online": "Connecté",
      "backend.offline": "Indisponible",
    });
  });

  it("matches selected glossary and form labels", () => {
    expect(english["auth.login.email"]).toBe("Email address");
    expect(french["auth.login.email"]).toBe("Courriel");
    expect(english["household.registrationHolder.firstName"]).toBe("First name");
    expect(french["household.registrationHolder.firstName"]).toBe("Prénom");
    expect(english["reservation.confirmation.pickupCode"]).toBe("Pickup code");
    expect(french["reservation.confirmation.pickupCode"]).toBe("Code de cueillette");
    expect(english["household.status.reviewRequired"]).toBe("Staff review required");
    expect(french["household.status.reviewRequired"]).toBe("Vérification par l'équipe requise");
  });

  it("resolves nested keys through i18next in both languages", async () => {
    const i18n = createInstance();
    await i18n.init({
      resources: { en: { translation: en }, fr: { translation: fr } },
      lng: "fr",
      fallbackLng: "fr",
      initAsync: false,
      interpolation: { escapeValue: false },
    });

    expect(i18n.getFixedT("en")("auth.login.title")).toBe("Sign in");
    expect(i18n.getFixedT("fr")("auth.login.title")).toBe("Connexion");
    expect(i18n.getFixedT("en")("backend.online")).toBe("Connected");
    expect(i18n.getFixedT("fr")("backend.online")).toBe("Connecté");
  });
});
