// AI contribution: 50% or more AI-generated
/**
 * Roles and their groups, from the generated API `Role` type (FIX-11 builds the
 * same groups from `User.Role` on the server). `AREA_OF` is a Record over every
 * API role, so a role added to the API does not compile until it has an area.
 * The role only shapes the interface; the server checks every permission.
 */
import type { components } from "../api/generated";

export type Role = components["schemas"]["RoleEnum"];

/** The part of the app a role works in. */
export type Area = "household" | "store" | "staff";

const AREA_OF: Record<Role, Area> = {
  beneficiary: "household",
  store_staff: "store",
  store_manager: "store",
  intake_worker: "staff",
  admin: "staff",
};

/** Every role the API knows. */
export const ROLES = Object.keys(AREA_OF) as readonly Role[];

/** The roles that work in an area, for example the store team. */
export function rolesIn(area: Area): readonly Role[] {
  return ROLES.filter((role) => AREA_OF[role] === area);
}

/** The roles of each area, used by the route guards and the menus. */
export const AREA_ROLES: Record<Area, readonly Role[]> = {
  household: rolesIn("household"),
  store: rolesIn("store"),
  staff: rolesIn("staff"),
};

export function isRole(value: unknown): value is Role {
  return typeof value === "string" && Object.hasOwn(AREA_OF, value);
}

/** The first screen of each area that exists today. */
const AREA_HOME: Record<Area, string> = {
  household: "/listings",
  store: "/store/listings/new",
  staff: "/staff/households",
};

/** Where each role lands after sign-in, or when it opens a screen it cannot use. */
export function homePathFor(role: Role): string {
  return AREA_HOME[AREA_OF[role]];
}
