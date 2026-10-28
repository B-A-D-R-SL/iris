// AI contribution: 50% or more AI-generated
import { QueryClient } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import axe from "axe-core";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { expect, vi } from "vitest";

import { AppProviders } from "../app/providers";
import type { CurrentUser, Role } from "../features/accounts/currentUser";

/** Renders inside the real providers (theme, dates, queries) and a router at `route`. */
export function renderWithProviders(ui: ReactNode, { route = "/" }: { route?: string } = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <AppProviders queryClient={queryClient} env="test">
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </AppProviders>,
  );
}

export function testUser(role: Role, overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    name: "Camille R.",
    role,
    store:
      role === "store_staff" || role === "store_manager"
        ? "00000000-0000-4000-8000-0000000000aa"
        : null,
    language: "fr",
    ...overrides,
  };
}

/** Fakes GET /api/me/: a user, signed out (401), or a server failure (500). */
export function mockCurrentUser(user: CurrentUser | "signed-out" | "server-error") {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.endsWith("/api/me/")) return new Response(null, { status: 404 });
    if (user === "signed-out") return new Response(null, { status: 401 });
    if (user === "server-error") return new Response(null, { status: 500 });
    return Response.json(user);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** WCAG checks with axe (NFR-03). Contrast needs a real browser, so it is checked by hand. */
export async function expectNoAxeViolations(container: Element) {
  const results = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
  expect(results.violations.map((violation) => `${violation.id}: ${violation.help}`)).toEqual([]);
}
