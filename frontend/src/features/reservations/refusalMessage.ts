// AI contribution: 50% or more AI-generated
/**
 * Which notice to show for a refused reservation (US-41), following the H1
 * mockup: 4a (sold out) and 4b (limit reached) are warnings with a title; the
 * rest are errors. The server's own text is never shown, only these messages.
 */
import { ReserveFailed } from "./api";

export const SOLD_OUT = "sold_out";
export const TOO_MANY_ACTIVE = "too_many_active_reservations";

export interface RefusalNotice {
  type: "warning" | "error";
  titleKey?: string;
  messageKey: string;
}

const NOTICES: Record<string, RefusalNotice> = {
  [SOLD_OUT]: {
    type: "warning",
    titleKey: "reservation.reserve.soldOutTitle",
    messageKey: "reservation.reserve.soldOut",
  },
  [TOO_MANY_ACTIVE]: {
    type: "warning",
    titleKey: "reservation.reserve.tooManyActiveTitle",
    messageKey: "reservation.reserve.tooManyActive",
  },
  not_enough_units: { type: "error", messageKey: "reservation.reserve.notEnough" },
  quantity_over_listing_limit: {
    type: "error",
    messageKey: "reservation.reserve.overListingLimit",
  },
  listing_not_available: { type: "error", messageKey: "reservation.reserve.notAvailable" },
  household_not_approved: { type: "error", messageKey: "reservation.reserve.notApproved" },
  reservations_unavailable: { type: "error", messageKey: "reservation.reserve.tryAgain" },
  pickup_code_unavailable: { type: "error", messageKey: "reservation.reserve.tryAgain" },
};

const FALLBACK: RefusalNotice = { type: "error", messageKey: "reservation.reserve.failed" };

/** The server's refusal code, or a generic one for a lost connection or an unknown answer. */
export function refusalCode(error: unknown): string {
  return error instanceof ReserveFailed ? error.code : "request_refused";
}

/** The notice for a refusal code; unknown codes get the generic "try again". */
export function refusalNotice(code: string): RefusalNotice {
  return Object.hasOwn(NOTICES, code) ? NOTICES[code] : FALLBACK;
}
