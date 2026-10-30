// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";
import { createInstance } from "i18next";

import en from "../shared/i18n/en.json";
import fr from "../shared/i18n/fr.json";

type TranslationTree = { [key: string]: string | TranslationTree };

/**
 * Flattens nested translations into dot-separated keys mapped to their values.
 * @param tree Translation entries to flatten.
 * @param prefix Parent key path prepended to each entry, if provided.
 * @returns A map of translation key paths to translated strings.
 */
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

  it("uses three-part keys with documented four-part option groups", () => {
    const segment = /^[a-z][a-zA-Z0-9]*$/;
    const optionGroups = new Set([
      "household.registrationMembers.relations",
      "store.partnerApplication.businessTypes",
      "store.partnerApplication.donationFrequency",
      "furniture.offer.conditionOptions",
    ]);
    for (const [language, entries] of [
      ["en", english],
      ["fr", french],
    ] as const) {
      for (const key of Object.keys(entries)) {
        const parts = key.split(".");
        const isOptionGroup = optionGroups.has(parts.slice(0, 3).join("."));
        expect(parts.length, `${language}: ${key}`).toBe(isOptionGroup ? 4 : 3);
        expect(
          parts.every((part) => segment.test(part)),
          `${language}: ${key}`,
        ).toBe(true);
      }
    }
  });

  it("keeps the welcome title and names the other language on the switch (SET-16)", () => {
    expect(english["public.welcome.title"]).toBe("Welcome to Iris");
    expect(french["public.welcome.title"]).toBe("Bienvenue sur Iris");
    expect(english["app.language.switchTo"]).toBe("Français");
    expect(french["app.language.switchTo"]).toBe("English");
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
    expect(i18n.getFixedT("en")("app.householdNav.listings")).toBe("Listings");
    expect(i18n.getFixedT("fr")("app.householdNav.listings")).toBe("Offres");
  });
});
