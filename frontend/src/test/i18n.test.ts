// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";
import { createInstance } from "i18next";

import { resources } from "../shared/i18n/resources";

type TranslationTree = { [key: string]: string | TranslationTree };
type TranslationCatalog = TranslationTree & { _meta: string };

/** Compare complete keys without depending on how entries are grouped. */
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

const english = flatten(resources.en.translation);
const french = flatten(resources.fr.translation);
const files = import.meta.glob<string>("../shared/i18n/{en,fr}/*.json", {
  eager: true,
  query: "?raw",
  import: "default",
});
const catalogs = Object.entries(files).map(([path, source]) => {
  const { _meta, ...entries } = JSON.parse(source) as TranslationCatalog;
  return {
    path,
    source,
    language: path.includes("/en/") ? "en" : "fr",
    declaration: _meta,
    entries,
  };
});

describe("translation catalog files", () => {
  it("has matching area files in French and English", () => {
    const englishFiles = catalogs.filter(({ language }) => language === "en");
    const frenchFiles = catalogs.filter(({ language }) => language === "fr");
    expect(englishFiles.length).toBeGreaterThan(0);
    expect(englishFiles.map(({ path }) => path.replace("/en/", "/fr/")).sort()).toEqual(
      frenchFiles.map(({ path }) => path).sort(),
    );
  });

  it.each(catalogs)(
    "keeps $path below 500 lines with matching nonempty keys",
    ({ path, source, language, declaration, entries }) => {
      expect(source.trimEnd().split("\n").length, path).toBeLessThan(500);
      expect(declaration, path).toBe("AI contribution: 50% or more AI-generated");
      const otherPath = path.replace(`/${language}/`, language === "en" ? "/fr/" : "/en/");
      const other = catalogs.find((catalog) => catalog.path === otherPath);
      expect(other, otherPath).toBeDefined();
      const values = flatten(entries);
      expect(Object.keys(values).sort()).toEqual(Object.keys(flatten(other!.entries)).sort());
      for (const [key, value] of Object.entries(values)) {
        expect(value.trim(), `${path}: ${key}`).not.toBe("");
      }
    },
  );

  it.each(["en", "fr"] as const)(
    "loads every %s file without overwriting another area",
    (language) => {
      const languageFiles = catalogs.filter((catalog) => catalog.language === language);
      const roots = languageFiles.flatMap(({ entries }) => Object.keys(entries));
      expect(new Set(roots).size).toBe(roots.length);
      const expected = Object.assign({}, ...languageFiles.map(({ entries }) => entries));
      expect(resources[language].translation).toEqual(expected);
    },
  );
});

describe("translation keys", () => {
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

describe("known translations", () => {
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

describe("i18next resource behavior", () => {
  it("resolves nested keys through i18next in both languages", async () => {
    const i18n = createInstance();
    await i18n.init({
      resources,
      lng: "fr",
      fallbackLng: "fr",
      initAsync: false,
      interpolation: { escapeValue: false },
    });

    expect(i18n.getFixedT("en")("auth.login.title")).toBe("Sign in");
    expect(i18n.getFixedT("fr")("auth.login.title")).toBe("Connexion");
    expect(i18n.getFixedT("en")("app.householdNav.listings")).toBe("Listings");
    expect(i18n.getFixedT("fr")("app.householdNav.listings")).toBe("Offres");
    for (const language of ["en", "fr"] as const) {
      for (const [key, value] of Object.entries(flatten(resources[language].translation))) {
        expect(i18n.getFixedT(language)(key), `${language}: ${key}`).toBe(value);
      }
    }
  });

  it("falls back to French across every area when English translations are missing", async () => {
    const i18n = createInstance();
    await i18n.init({
      resources: { en: { translation: {} }, fr: resources.fr },
      lng: "en",
      fallbackLng: "fr",
      initAsync: false,
      interpolation: { escapeValue: false },
    });

    for (const [key, value] of Object.entries(french)) {
      expect(i18n.t(key), key).toBe(value);
    }
  });

  it("returns the key when a translation is missing", async () => {
    const i18n = createInstance();
    await i18n.init({
      resources,
      lng: "en",
      fallbackLng: "fr",
      initAsync: false,
      interpolation: { escapeValue: false },
    });

    expect(i18n.t("public.welcome.missing")).toBe("public.welcome.missing");
  });
});
