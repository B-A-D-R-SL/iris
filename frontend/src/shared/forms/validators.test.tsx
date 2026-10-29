// AI contribution: 50% or more AI-generated
import { act, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import i18n from "../i18n";
import {
  allOf,
  fileTypeNames,
  hasLength,
  isAcceptedFile,
  isDateInRange,
  isMoneyInRange,
  isPhone,
  isPostalCode,
  isRequired,
} from "./validators";

/** The text a rule shows under the field, in the current language. */
function messageOf(error: ReactNode): string {
  const { container, unmount } = render(<>{error}</>);
  const text = container.textContent ?? "";
  unmount();
  return text.replace(/\s/g, " ");
}

function file(name: string, type: string, sizeBytes: number): File {
  return new File([new Uint8Array(sizeBytes)], name, { type });
}

describe("rules accept valid and empty values", () => {
  it.each([
    ["hasLength", hasLength({ min: 2, max: 80 }), "Pains de la veille"],
    ["isPostalCode", isPostalCode(), "H2X 1Y4"],
    ["isPhone", isPhone(), "+15145550123"],
    ["isMoneyInRange", isMoneyInRange({ maxCents: 100_000 }), 100_000],
    ["isDateInRange", isDateInRange({ min: "2026-10-11" }), "2026-10-11"],
    [
      "isAcceptedFile",
      isAcceptedFile({ types: ["image/png"], maxMb: 5 }),
      file("a.png", "image/png", 10),
    ],
  ] as const)("%s accepts a valid value", (_name, rule, value) => {
    expect((rule as (v: unknown) => ReactNode)(value)).toBeNull();
  });

  it.each([
    ["hasLength", hasLength({ min: 2, max: 80 }), ""],
    ["isPostalCode", isPostalCode(), ""],
    ["isPhone", isPhone(), ""],
    ["isMoneyInRange", isMoneyInRange({ maxCents: 100 }), null],
    ["isDateInRange", isDateInRange(), null],
    ["isAcceptedFile", isAcceptedFile({ types: ["image/png"], maxMb: 5 }), null],
  ] as const)("%s leaves an empty optional value alone", (_name, rule, value) => {
    expect((rule as (v: unknown) => ReactNode)(value)).toBeNull();
  });
});

describe("rules explain the problem in French by default", () => {
  it.each([
    [isRequired(), "   ", "Remplissez ce champ."],
    [isRequired(), null, "Remplissez ce champ."],
    [hasLength({ min: 2, max: 80 }), "A", "Entrez de 2 à 80 caractères."],
    [hasLength({ max: 500 }), "x".repeat(501), "Entrez au plus 500 caractères."],
    [isPostalCode(), "H2X 1Y", "Entrez un code postal canadien, par exemple H2X 1Y4."],
    [isPhone(), "514555", "Entrez un numéro de 10 chiffres, par exemple (514) 555-0123."],
    [isPhone(), "+10145550123", "Entrez un numéro de 10 chiffres, par exemple (514) 555-0123."],
    [isMoneyInRange({ maxCents: 100_000 }), 100_001, "Entrez un montant de 0,00 $ à 1 000,00 $."],
    [isDateInRange(), "2026-13-45", "Entrez une date au format AAAA-MM-JJ."],
    [isDateInRange({ min: "2026-10-11" }), "2026-10-10", "Choisissez le 2026-10-11 ou après."],
    [isDateInRange({ max: "2026-10-11" }), "2026-10-12", "Choisissez le 2026-10-11 ou avant."],
  ])("%#: %j", (rule, value, expected) => {
    expect(messageOf((rule as (v: unknown) => ReactNode)(value))).toBe(expected);
  });

  it.each(["2026-02-31", "2026-02-29", "2026-04-31", "2026-06-31"])(
    "refuses %s, which does not exist on the calendar",
    (value) => {
      expect(messageOf(isDateInRange()(value))).toBe("Entrez une date au format AAAA-MM-JJ.");
    },
  );

  it.each(["2028-02-29", "2026-01-31", "2026-12-31"])("accepts the real date %s", (value) => {
    expect(isDateInRange()(value)).toBeNull();
  });

  it("refuses a file of the wrong type or too large", () => {
    const rule = isAcceptedFile({ types: ["image/jpeg", "image/png"], maxMb: 5 });
    expect(messageOf(rule(file("notice.pdf", "application/pdf", 10)))).toBe(
      "Choisissez un fichier JPG, PNG.",
    );
    expect(messageOf(rule(file("big.png", "image/png", 5 * 1024 * 1024 + 1)))).toBe(
      "Choisissez un fichier de 5 Mo ou moins.",
    );
  });
});

describe("messages follow the language switch", () => {
  it("re-renders an error already on screen in English", async () => {
    render(<>{isMoneyInRange({ maxCents: 100_000 })(-1)}</>);
    expect(screen.getByText(/Entrez un montant/)).toBeInTheDocument();

    await act(() => i18n.changeLanguage("en"));

    expect(screen.getByText("Enter an amount from $0.00 to $1,000.00.")).toBeInTheDocument();
  });
});

describe("allOf", () => {
  it("returns the first failing rule, in order", () => {
    const rule = allOf(isRequired(), isPostalCode());
    expect(messageOf(rule(""))).toBe("Remplissez ce champ.");
    expect(messageOf(rule("H2X"))).toMatch(/code postal/);
    expect(rule("H2X 1Y4")).toBeNull();
  });
});

describe("fileTypeNames", () => {
  it("names common types the way people know them", () => {
    expect(fileTypeNames(["image/jpeg", "image/png", "application/pdf"])).toBe("JPG, PNG, PDF");
  });
});
