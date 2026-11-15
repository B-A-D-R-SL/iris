// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import { quantityToSend } from "./quantity";

describe("quantityToSend", () => {
  it.each([
    [1, 2, 1],
    [2, 2, 2],
    [9, 2, 2], // typed past the cap
    [0, 2, 1],
    [-3, 2, 1],
    ["2", 3, 2],
    ["", 3, 1], // field cleared
    ["abc", 3, 1],
    [2.7, 3, 2],
  ])("sends %j with a cap of %i as %i", (value, cap, expected) => {
    expect(quantityToSend(value, cap)).toBe(expected);
  });
});
