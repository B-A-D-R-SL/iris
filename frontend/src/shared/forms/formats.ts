// AI contribution: 50% or more AI-generated
/**
 * Pure conversions between what people type and what the API stores
 * (forms-and-fields.md, "Shared rules"). No React here, so they are easy to test.
 */

/** "h2x1y4" -> "H2X 1Y4"; partial input keeps its shape: "h2x1" -> "H2X 1". */
export function normalizePostalCode(input: string): string {
  const compact = input
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .slice(0, 6);
  return compact.length > 3 ? `${compact.slice(0, 3)} ${compact.slice(3)}` : compact;
}

/** Up to 10 digits of a Canadian number; a leading country code 1 is dropped. */
export function phoneDigits(input: string): string {
  let digits = input.replace(/\D/g, "");
  if (input.trim().startsWith("+1") || (digits.length === 11 && digits.startsWith("1"))) {
    digits = digits.slice(1);
  }
  return digits.slice(0, 10);
}

/** "5145550123" -> "(514) 555-0123", formatting partial numbers as they are typed. */
export function formatPhone(digits: string): string {
  if (digits.length === 0) return "";
  if (digits.length <= 3) return `(${digits}`;
  if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
}

/** Ten digits become E.164 ("+15145550123"); anything shorter is returned as typed digits. */
export function toPhoneValue(digits: string): string {
  return digits.length === 10 ? `+1${digits}` : digits;
}

/** Dollars typed in the field -> integer cents (Rule: money is integer cents). */
export function dollarsToCents(dollars: number): number {
  return Math.round(dollars * 100);
}

export function centsToDollars(cents: number): number {
  return cents / 100;
}

/** 1050 -> "10,50 $" (fr) or "$10.50" (en). */
export function formatMoney(cents: number, language: string): string {
  return new Intl.NumberFormat(language === "en" ? "en-CA" : "fr-CA", {
    style: "currency",
    currency: "CAD",
    currencyDisplay: "narrowSymbol",
  }).format(centsToDollars(cents));
}
