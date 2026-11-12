// AI contribution: 50% or more AI-generated
/**
 * Pickup-code helpers for the store Confirm screen (US-44). Mirrors the
 * backend's normalize_code: uppercase and drop spaces; the API still checks
 * length and alphabet.
 */

export const CODE_LENGTH = 6;

/** Uppercase a typed or scanned value and drop its spaces. */
export function normalizeCode(raw: string): string {
  return raw.replace(/\s+/g, "").toUpperCase();
}

/**
 * Keep only letters and digits while typing, capped at the stored length, so
 * the field matches what staff see on the QR and on the household screen.
 */
export function draftCode(raw: string): string {
  return normalizeCode(raw)
    .replace(/[^A-Z0-9]/g, "")
    .slice(0, CODE_LENGTH);
}

/** True when the draft is ready to look up (exact stored length). */
export function isCompleteCode(code: string): boolean {
  return code.length === CODE_LENGTH;
}

/**
 * Accept a bare 6-character code, or a complete 6-character token bounded by
 * non-alnum characters. Never truncate a longer alphanumeric string.
 */
export function codeFromScan(raw: string): string | null {
  const normalized = normalizeCode(raw);
  if (/^[A-Z0-9]{6}$/.test(normalized)) return normalized;
  const re = /(?:^|[^A-Z0-9])([A-Z0-9]{6})(?![A-Z0-9])/g;
  let last: string | null = null;
  for (const match of normalized.matchAll(re)) {
    last = match[1];
  }
  return last;
}
