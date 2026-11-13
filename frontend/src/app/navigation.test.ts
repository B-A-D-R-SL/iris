// AI contribution: 50% or more AI-generated
import { IconHome } from "@tabler/icons-react";
import { describe, expect, it } from "vitest";

import { homePathFor, ROLES } from "../shared/auth/roles";
import { activeNavPath, NAVIGATION, navFor, type NavItem } from "./navigation";

const paths = (items: { path: string }[]) => items.map((item) => item.path);

describe("navFor follows the permission matrix (business-rules.md)", () => {
  it("gives households the listings tab", () => {
    expect(paths(navFor("household", "beneficiary"))).toEqual(["/listings"]);
  });

  it.each(["store_staff", "store_manager"] as const)("gives %s the posting tab", (role) => {
    expect(paths(navFor("store", role))).toEqual(["/store/listings/new"]);
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

  it("has no tab for a screen that is not built (FIX-13)", () => {
    const all = paths(Object.values(NAVIGATION).flat());
    for (const placeholder of ["/home", "/reservations", "/profile", "/store", "/store/confirm"]) {
      expect(all).not.toContain(placeholder);
    }
    expect(all).not.toContain("/staff/review");
    expect(all).not.toContain("/staff/stores");
  });
});

describe("homePathFor", () => {
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
  const tab = (path: string): NavItem => ({ path, labelKey: "", icon: IconHome, roles: [] });
  const items = [tab("/store/listings"), tab("/store/listings/new")];

  it.each([
    ["/store/listings", "/store/listings"],
    ["/store/listings/new", "/store/listings/new"],
    ["/store/listings/42/edit", "/store/listings"],
  ])("highlights the most specific tab for %s", (pathname, expected) => {
    expect(activeNavPath(items, pathname)).toBe(expected);
  });

  it("highlights the listings tab on a listing detail", () => {
    expect(activeNavPath(NAVIGATION.household, "/listings/42")).toBe("/listings");
  });

  it("does not match a path that only shares a prefix", () => {
    expect(activeNavPath(NAVIGATION.household, "/listingsx")).toBeNull();
  });
});
