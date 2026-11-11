// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import { CODE_LENGTH, codeFromScan, draftCode, isCompleteCode, normalizeCode } from "./confirmCode";

describe("confirmCode", () => {
  it("uppercases and drops spaces like the API", () => {
    expect(normalizeCode(" p4 wz 8h ")).toBe("P4WZ8H");
    expect(draftCode("p4wz8h!!!")).toBe("P4WZ8H");
    expect(draftCode("ABCDEFGH")).toBe("ABCDEF");
    expect(CODE_LENGTH).toBe(6);
    expect(isCompleteCode("P4WZ8H")).toBe(true);
    expect(isCompleteCode("P4WZ8")).toBe(false);
  });

  it("reads a bare code or the last six-character token from a scan", () => {
    expect(codeFromScan("p4wz8h")).toBe("P4WZ8H");
    expect(codeFromScan("IRIS-P4WZ8H")).toBe("P4WZ8H");
    expect(codeFromScan("no-code-here")).toBeNull();
  });
});
