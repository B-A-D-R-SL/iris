// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import en from "../../shared/i18n/en/household.json";
import fr from "../../shared/i18n/fr/household.json";
import { ReserveFailed } from "./api";
import { refusalCode, refusalNotice } from "./refusalMessage";

/** The text a reserve key points to, in one language. */
function text(catalog: typeof fr, key: string): string {
  const name = key.replace("reservation.reserve.", "") as keyof typeof fr.reservation.reserve;
  return catalog.reservation.reserve[name];
}

describe("refusalNotice", () => {
  it.each([
    ["sold_out", "warning", "Cette offre vient d'être réservée au complet"],
    [
      "too_many_active_reservations",
      "warning",
      "Vous avez déjà le nombre maximal de réservations actives",
    ],
  ])("gives %s a titled %s, as mockup H1 4a and 4b", (code, type, title) => {
    const notice = refusalNotice(code);
    expect(notice.type).toBe(type);
    expect(text(fr, notice.titleKey ?? "")).toBe(title);
  });

  it.each([
    ["not_enough_units", "Il n'en reste pas assez. Choisissez une plus petite quantité."],
    ["quantity_over_listing_limit", "C'est plus qu'un foyer peut réserver pour cette offre."],
    ["listing_not_available", "Cette offre n'est plus disponible."],
    ["household_not_approved", "Seuls les foyers approuvés peuvent réserver."],
    [
      "reservations_unavailable",
      "La réservation n'est pas disponible pour le moment. Réessayez plus tard.",
    ],
    [
      "pickup_code_unavailable",
      "La réservation n'est pas disponible pour le moment. Réessayez plus tard.",
    ],
  ])("gives %s its own error message", (code, message) => {
    const notice = refusalNotice(code);
    expect(notice).toMatchObject({ type: "error" });
    expect(notice.titleKey).toBeUndefined();
    expect(text(fr, notice.messageKey)).toBe(message);
  });

  it.each(["request_refused", "something_new", "constructor", "toString", ""])(
    "falls back to the generic message for %j",
    (code) => {
      expect(refusalNotice(code)).toEqual({
        type: "error",
        messageKey: "reservation.reserve.failed",
      });
    },
  );

  it("has every message in English too", () => {
    for (const code of ["sold_out", "too_many_active_reservations", "not_enough_units", "x"]) {
      const notice = refusalNotice(code);
      expect(text(en, notice.messageKey)).toBeTruthy();
    }
  });
});

describe("refusalCode", () => {
  it("uses the server's code for a refused reservation", () => {
    expect(refusalCode(new ReserveFailed(409, "sold_out", "server text"))).toBe("sold_out");
  });

  it("uses a generic code for anything else", () => {
    expect(refusalCode(new TypeError("Failed to fetch"))).toBe("request_refused");
  });
});
