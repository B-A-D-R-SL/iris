// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import { ROLES } from "../features/accounts/currentUser";
import { activeNavPath, homePathFor, NAVIGATION, navFor } from "./navigation";

const paths = (items: { path: string }[]) => items.map((item) => item.path);

describe("navFor follows the permission matrix (business-rules.md)", () => {
  it("gives households their four tabs", () => {
    expect(paths(navFor("household", "beneficiary"))).toEqual([
      "/home",
      "/listings",
      "/reservations",
      "/profile",
    ]);
  });

  it.each(["store_staff", "store_manager"] as const)("gives %s the four store tabs", (role) => {
    expect(paths(navFor("store", role))).toEqual([
      "/store",
      "/store/confirm",
      "/store/listings/new",
      "/store/listings",
    ]);
  });

  it("limits intake workers to households and walk-in registration", () => {
    expect(paths(navFor("staff", "intake_worker"))).toEqual([
      "/staff/households",
      "/staff/walk-in",
    ]);
  });

  it("gives admins every staff screen", () => {
    expect(paths(navFor("staff", "admin"))).toEqual(paths([...NAVIGATION.staff]));
  });

  it.each(ROLES.filter((role) => role !== "beneficiary"))(
    "shows no household tab to %s",
    (role) => {
      expect(navFor("household", role)).toEqual([]);
    },
  );

  it.each(["beneficiary", "intake_worker", "admin"] as const)(
    "shows no store tab to %s",
    (role) => {
      expect(navFor("store", role)).toEqual([]);
    },
  );
});

describe("homePathFor", () => {
  it.each([
    ["beneficiary", "/home"],
    ["store_staff", "/store"],
    ["store_manager", "/store"],
    ["intake_worker", "/staff/households"],
    ["admin", "/staff/households"],
  ] as const)("sends %s to %s", (role, path) => {
    expect(homePathFor(role)).toBe(path);
  });

  it("only sends a role to a screen it may open", () => {
    for (const role of ROLES) {
      const allowed = (["household", "store", "staff"] as const).flatMap((area) =>
        paths(navFor(area, role)),
      );
      expect(allowed).toContain(homePathFor(role));
    }
  });
});

describe("activeNavPath", () => {
  const store = NAVIGATION.store;

  it.each([
    ["/store", "/store"],
    ["/store/confirm", "/store/confirm"],
    ["/store/listings/new", "/store/listings/new"],
    ["/store/listings", "/store/listings"],
    ["/store/listings/42/edit", "/store/listings"],
  ])("highlights the most specific tab for %s", (pathname, expected) => {
    expect(activeNavPath(store, pathname)).toBe(expected);
  });

  it("highlights the listings tab on a listing detail", () => {
    expect(activeNavPath(NAVIGATION.household, "/listings/42")).toBe("/listings");
  });

  it("does not match a path that only shares a prefix", () => {
    expect(activeNavPath(NAVIGATION.household, "/homes")).toBeNull();
  });
});
