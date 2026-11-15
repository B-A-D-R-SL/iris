// AI contribution: 50% or more AI-generated
/** What to send: a whole number from 1 to `cap`, whatever is in the quantity field (US-41). */
export function quantityToSend(value: number | string, cap: number): number {
  const typed = Math.trunc(Number(value));
  return Number.isFinite(typed) ? Math.min(cap, Math.max(1, typed)) : 1;
}
