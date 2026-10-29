// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import {
  centsToDollars,
  dollarsToCents,
  formatMoney,
  formatPhone,
  normalizePostalCode,
  phoneDigits,
  toPhoneValue,
} from "./formats";

describe("normalizePostalCode", () => {
  it.each([
    ["h2x1y4", "H2X 1Y4"],
    ["H2X 1Y4", "H2X 1Y4"],
    ["h2x-1y4", "H2X 1Y4"],
    ["h2x", "H2X"],
    ["h2x1", "H2X 1"],
    ["H2X 1Y45", "H2X 1Y4"],
    ["", ""],
  ])("%j becomes %j", (input, expected) => {
    expect(normalizePostalCode(input)).toBe(expected);
  });
});

describe("phone numbers", () => {
  it.each([
    ["5145550123", "5145550123"],
    ["(514) 555-0123", "5145550123"],
    ["+1 514 555 0123", "5145550123"],
    ["1-514-555-0123", "5145550123"],
    ["514555012399", "5145550123"],
    ["514", "514"],
    ["", ""],
  ])("keeps the 10 national digits of %j", (input, expected) => {
    expect(phoneDigits(input)).toBe(expected);
  });

  it.each([
    ["", ""],
    ["5", "(5"],
    ["514", "(514"],
    ["5145", "(514) 5"],
    ["514555", "(514) 555"],
    ["5145550", "(514) 555-0"],
    ["5145550123", "(514) 555-0123"],
  ])("shows %j as %j while typing", (digits, expected) => {
    expect(formatPhone(digits)).toBe(expected);
  });

  it("stores E.164 only once the number is complete", () => {
    expect(toPhoneValue("5145550123")).toBe("+15145550123");
    expect(toPhoneValue("514555")).toBe("514555");
  });

  it("reads a stored E.164 value back for display", () => {
    expect(formatPhone(phoneDigits("+15145550123"))).toBe("(514) 555-0123");
  });
});

describe("money", () => {
  it.each([
    [0, 0],
    [12.5, 1250],
    [0.29, 29],
    [1000, 100000],
  ])("$%d is %d cents", (dollars, cents) => {
    expect(dollarsToCents(dollars)).toBe(cents);
    expect(centsToDollars(cents)).toBe(dollars);
  });

  it("formats cents in each language", () => {
    expect(formatMoney(1050, "fr").replace(/\s/g, " ")).toBe("10,50 $");
    expect(formatMoney(1050, "en")).toBe("$10.50");
    expect(formatMoney(100000, "en")).toBe("$1,000.00");
  });
});
