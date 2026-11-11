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

describe("SET-13 translation catalogs", () => {
  it("keeps household and category status wording only in the shared status catalog", () => {
    for (const entries of [english, french]) {
      expect(Object.keys(entries).some((key) => key.startsWith("household.status."))).toBe(false);
      expect(entries["category.admin.active"]).toBeUndefined();
      expect(entries["category.admin.inactive"]).toBeUndefined();
      expect(entries["shared.status.category.active"]).toBe("Active");
      expect(entries["shared.status.category.inactive"]).toBe("Inactive");
    }
  });

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
});

describe("SET-13 translation keys", () => {
  it("uses three-part keys with documented four-part option groups", () => {
    const segment = /^[a-z][a-zA-Z0-9]*$/;
    const statusSegment = /^[a-z][a-z0-9_]*$/;
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
        const isStatus = parts[0] === "shared" && parts[1] === "status";
        const isOptionGroup = isStatus || optionGroups.has(parts.slice(0, 3).join("."));
        expect(parts.length, `${language}: ${key}`).toBe(isOptionGroup ? 4 : 3);
        expect(
          parts.every((part, index) =>
            (isStatus && index === 3 ? statusSegment : segment).test(part),
          ),
          `${language}: ${key}`,
        ).toBe(true);
      }
    }
  });
});

describe("SET-13 glossary and shell labels", () => {
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
    expect(english["shared.status.household.review_required"]).toBe("Staff review required");
    expect(french["shared.status.household.review_required"]).toBe(
      "Vérification par l'équipe requise",
    );
  });
});

describe("SET-13 i18next resolution", () => {
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
