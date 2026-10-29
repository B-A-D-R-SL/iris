// AI contribution: 50% or more AI-generated
/**
 * Navigation of each area: one place decides which roles see which screen.
 * Tabs come from the Figma bottom navs and staff side nav (SET-11); roles come
 * from the permission matrix in business-rules.md. The server still checks
 * every permission; this only shapes the interface.
 */
import {
  IconBuilding,
  IconBuildingStore,
  IconCalendarEvent,
  IconCategory,
  IconCircleCheck,
  IconCirclePlus,
  IconClipboardList,
  IconHome,
  IconPackage,
  IconScan,
  IconShoppingBag,
  IconTicket,
  IconUser,
  type TablerIcon,
} from "@tabler/icons-react";

import type { Role } from "../features/accounts/currentUser";

export type Area = "household" | "store" | "staff";

export interface NavItem {
  path: string;
  labelKey: string;
  icon: TablerIcon;
  roles: readonly Role[];
}

export const AREA_ROLES: Record<Area, readonly Role[]> = {
  household: ["beneficiary"],
  store: ["store_staff", "store_manager"],
  staff: ["intake_worker", "admin"],
};

const BENEFICIARY = AREA_ROLES.household;
const STORE_TEAM = AREA_ROLES.store;
const STAFF = AREA_ROLES.staff;
const ADMIN: readonly Role[] = ["admin"];

export const NAVIGATION: Record<Area, readonly NavItem[]> = {
  household: [
    { path: "/home", labelKey: "app.householdNav.home", icon: IconHome, roles: BENEFICIARY },
    {
      path: "/listings",
      labelKey: "app.householdNav.listings",
      icon: IconShoppingBag,
      roles: BENEFICIARY,
    },
    {
      path: "/reservations",
      labelKey: "app.householdNav.reservations",
      icon: IconTicket,
      roles: BENEFICIARY,
    },
    { path: "/profile", labelKey: "app.householdNav.profile", icon: IconUser, roles: BENEFICIARY },
  ],
  store: [
    { path: "/store", labelKey: "app.storeNav.today", icon: IconCalendarEvent, roles: STORE_TEAM },
    { path: "/store/confirm", labelKey: "app.storeNav.confirm", icon: IconScan, roles: STORE_TEAM },
    {
      path: "/store/listings/new",
      labelKey: "app.storeNav.post",
      icon: IconCirclePlus,
      roles: STORE_TEAM,
    },
    {
      path: "/store/listings",
      labelKey: "app.storeNav.myListings",
      icon: IconPackage,
      roles: STORE_TEAM,
    },
  ],
  staff: [
    {
      path: "/staff/households",
      labelKey: "app.staffNav.households",
      icon: IconHome,
      roles: STAFF,
    },
    {
      path: "/staff/review",
      labelKey: "app.staffNav.reviews",
      icon: IconCircleCheck,
      roles: ADMIN,
    },
    { path: "/staff/walk-in", labelKey: "app.staffNav.walkIn", icon: IconUser, roles: STAFF },
    {
      path: "/staff/partners",
      labelKey: "app.staffNav.partners",
      icon: IconBuildingStore,
      roles: ADMIN,
    },
    { path: "/staff/stores", labelKey: "app.staffNav.stores", icon: IconBuilding, roles: ADMIN },
    {
      path: "/staff/categories",
      labelKey: "app.staffNav.categories",
      icon: IconCategory,
      roles: ADMIN,
    },
    {
      path: "/staff/audit",
      labelKey: "app.staffNav.auditLog",
      icon: IconClipboardList,
      roles: ADMIN,
    },
  ],
};

/** The screens of an area that a role may open, in menu order. */
export function navFor(area: Area, role: Role): NavItem[] {
  return NAVIGATION[area].filter((item) => item.roles.includes(role));
}

/** Where each role lands after sign-in, or when it opens a screen it cannot use. */
export function homePathFor(role: Role): string {
  switch (role) {
    case "beneficiary":
      return "/home";
    case "store_staff":
    case "store_manager":
      return "/store";
    case "intake_worker":
    case "admin":
      return "/staff/households";
  }
}

function isWithin(pathname: string, path: string): boolean {
  return pathname === path || pathname.startsWith(`${path}/`);
}

/**
 * The menu item to highlight: the longest item path that contains the current
 * page, so /store/listings/new highlights "Publier", not "Mes offres".
 */
export function activeNavPath(items: readonly NavItem[], pathname: string): string | null {
  return items.reduce<string | null>(
    (best, item) =>
      isWithin(pathname, item.path) && (best === null || item.path.length > best.length)
        ? item.path
        : best,
    null,
  );
}
