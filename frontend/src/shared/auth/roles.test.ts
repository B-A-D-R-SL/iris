// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import { AREA_ROLES, homePathFor, isRole, ROLES, rolesIn, type Role } from "./roles";

describe("role groups (built from the API Role type, like FIX-11 on the server)", () => {
  it("knows every role of the API", () => {
    expect([...ROLES].sort()).toEqual(
      ["admin", "beneficiary", "intake_worker", "store_manager", "store_staff"].sort(),
    );
  });

  it("groups the roles by area, as business-rules.md does", () => {
    expect(AREA_ROLES).toEqual({
      household: ["beneficiary"],
      store: ["store_staff", "store_manager"],
      staff: ["intake_worker", "admin"],
    });
  });

  it("puts each role in exactly one area", () => {
    const grouped = (["household", "store", "staff"] as const).flatMap((area) => rolesIn(area));
    expect([...grouped].sort()).toEqual([...ROLES].sort());
  });
});

describe("isRole", () => {
  it.each(ROLES)("accepts %s", (role) => {
    expect(isRole(role)).toBe(true);
  });

  it.each(["superuser", "ADMIN", "", "toString", "constructor", 1, null, undefined])(
    "refuses %s",
    (value) => {
      expect(isRole(value)).toBe(false);
    },
  );
});

describe("homePathFor", () => {
  it.each([
    ["beneficiary", "/listings"],
    ["store_staff", "/store/listings/new"],
    ["store_manager", "/store/listings/new"],
    ["intake_worker", "/staff/households"],
    ["admin", "/staff/households"],
  ] satisfies [Role, string][])("sends %s to %s, a screen that exists", (role, path) => {
    expect(homePathFor(role)).toBe(path);
  });
});
