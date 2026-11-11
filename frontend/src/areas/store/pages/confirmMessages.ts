// AI contribution: 50% or more AI-generated
/**
 * Maps pickup API refusal codes to the Confirm screen's own French/English
 * copy (backend domain/pickup.py: the scan screen owns the wording).
 */

const REFUSAL_KEYS = {
  unknown_code: "unknownCode",
  unknown_reservation: "unknownReservation",
  wrong_store: "wrongStore",
  ambiguous_code: "ambiguousCode",
  already_picked_up: "alreadyPickedUp",
  cancelled: "cancelled",
  no_show: "noShow",
  not_open_yet: "notOpenYet",
  window_ended: "windowEnded",
  validation_error: "validationError",
  unavailable: "unavailable",
} as const;

export type RefusalCode = keyof typeof REFUSAL_KEYS;

export function isRefusalCode(code: string): code is RefusalCode {
  return Object.hasOwn(REFUSAL_KEYS, code);
}

function stem(code: string): string {
  return isRefusalCode(code) ? REFUSAL_KEYS[code] : REFUSAL_KEYS.unavailable;
}

/** i18n key under reservation.confirm.* for a refusal title. */
export function refusalTitleKey(code: string): string {
  return `reservation.confirm.${stem(code)}Title`;
}

export function refusalBodyKey(code: string): string {
  return `reservation.confirm.${stem(code)}Body`;
}
