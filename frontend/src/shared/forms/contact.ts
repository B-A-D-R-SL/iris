// AI contribution: 50% or more AI-generated
/** Complete contact values follow the same contract as modules.common.domain.contact. */
import { COMBINING_MARK, PYTHON_UNASSIGNED } from "./unicodeCombining";

const POSTAL_CODE = /^[ABCEGHJ-NPRSTVXY][0-9][ABCEGHJ-NPRSTV-Z][0-9][ABCEGHJ-NPRSTV-Z][0-9]$/;
const CANADIAN_PHONE = /^\+1[2-9][0-9]{9}$/;
// Python str.isspace()/re \s includes these controls, but excludes JavaScript's FEFF.
function withoutWhitespace(value: string): string {
  return value
    .replace(/\p{White_Space}/gu, "")
    .replaceAll("\u001c", "")
    .replaceAll("\u001d", "")
    .replaceAll("\u001e", "")
    .replaceAll("\u001f", "");
}

export function isBlankContact(value: string | null | undefined): boolean {
  return value == null || withoutWhitespace(value) === "";
}

/** Preserve US-17's uppercase, Unicode compatibility and accent folding. */
export function compactPostalCode(value: string): string {
  // A newer browser Unicode table must not fold backend-unknown characters into a valid code.
  if (PYTHON_UNASSIGNED.test(value)) return value;
  return withoutWhitespace(value.toUpperCase().normalize("NFKD").replace(COMBINING_MARK, ""));
}

export function canonicalPostalCode(value: string): string | null {
  const compact = compactPostalCode(value);
  return POSTAL_CODE.test(compact) ? `${compact.slice(0, 3)} ${compact.slice(3)}` : null;
}

/** Remove familiar display punctuation, retaining letters, extra digits and other prefixes. */
export function compactPhone(value: string): string {
  return withoutWhitespace(value.replace(/[().-]/g, ""));
}

export function normalizePhone(value: string): string | null {
  let compact = compactPhone(value);
  if (/^[0-9]{10}$/.test(compact)) compact = `+1${compact}`;
  else if (/^1[0-9]{10}$/.test(compact)) compact = `+${compact}`;
  return CANADIAN_PHONE.test(compact) ? compact : null;
}
