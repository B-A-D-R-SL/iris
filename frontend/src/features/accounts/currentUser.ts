// AI contribution: 50% or more AI-generated
/**
 * The signed-in user, read from GET /api/me/ (US-01, T-01.01.2).
 *
 * The role only decides what the interface shows. Every permission is checked
 * again by the server on each request (deny by default, SEC-05).
 */
import { useQuery } from "@tanstack/react-query";

import type { components, paths } from "../../shared/api/generated";

export type Role = components["schemas"]["RoleEnum"];

export const ROLES = [
  "beneficiary",
  "store_staff",
  "store_manager",
  "intake_worker",
  "admin",
] as const satisfies readonly Role[];

type CurrentUserResponse =
  paths["/api/me/"]["get"]["responses"][200]["content"]["application/json"];

export type CurrentUser = CurrentUserResponse;

export const CURRENT_USER_QUERY_KEY = ["current-user"] as const;

function isRole(value: unknown): value is Role {
  return typeof value === "string" && (ROLES as readonly string[]).includes(value);
}

function parseCurrentUser(data: unknown): CurrentUser {
  if (typeof data !== "object" || data === null) {
    throw new Error("Invalid current user response");
  }
  const { id, name, role, store, language } = data as Record<string, unknown>;
  if (
    typeof id !== "string" ||
    typeof name !== "string" ||
    !isRole(role) ||
    (store !== null && typeof store !== "string") ||
    (language !== "fr" && language !== "en")
  ) {
    throw new Error("Invalid current user response");
  }
  return { id, name, role, store, language };
}

/** Returns the signed-in user, or null when nobody is signed in. */
export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const response = await fetch("/api/me/", { headers: { Accept: "application/json" } });

  if (response.status === 401 || response.status === 403) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Current user unavailable: ${response.status}`);
  }
  return parseCurrentUser(await response.json());
}

export function useCurrentUser() {
  return useQuery({
    queryKey: CURRENT_USER_QUERY_KEY,
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60 * 1000,
  });
}
