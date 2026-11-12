// AI contribution: 50% or more AI-generated
/**
 * Navigation of each area: one place decides which roles see which screen.
 * Tabs come from the Figma bottom navs and staff side nav (SET-11); roles come
 * from the permission matrix in business-rules.md, grouped in shared/auth/roles.ts.
 * Only built screens have an entry: each story adds its own tab with its route.
 * The server still checks every permission; this only shapes the interface.
 */
import {
  IconBuildingStore,
  IconCategory,
  IconCirclePlus,
  IconClipboardList,
  IconHome,
  IconShoppingBag,
  IconUser,
  type TablerIcon,
} from "@tabler/icons-react";

import { AREA_ROLES, type Area, type Role } from "../shared/auth/roles";

export interface NavItem {
  path: string;
  labelKey: string;
  icon: TablerIcon;
  roles: readonly Role[];
}

const ADMIN: readonly Role[] = ["admin"];

export const NAVIGATION: Record<Area, readonly NavItem[]> = {
  household: [
    {
      path: "/listings",
      labelKey: "app.householdNav.listings",
      icon: IconShoppingBag,
      roles: AREA_ROLES.household,
    },
  ],
  store: [
    {
      path: "/store/listings/new",
      labelKey: "app.storeNav.post",
      icon: IconCirclePlus,
      roles: AREA_ROLES.store,
    },
  ],
  staff: [
    {
      path: "/staff/households",
      labelKey: "app.staffNav.households",
      icon: IconHome,
      roles: AREA_ROLES.staff,
    },
    {
      path: "/staff/walk-in",
      labelKey: "app.staffNav.walkIn",
      icon: IconUser,
      roles: AREA_ROLES.staff,
    },
    {
      path: "/staff/partners",
      labelKey: "app.staffNav.partners",
      icon: IconBuildingStore,
      roles: ADMIN,
    },
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

function isWithin(pathname: string, path: string): boolean {
  return pathname === path || pathname.startsWith(`${path}/`);
}

/**
 * The menu item to highlight: the longest item path that contains the current
 * page, so a sub-screen such as /listings/42 still highlights its tab.
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
