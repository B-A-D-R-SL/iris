// AI contribution: 50% or more AI-generated
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "../../../app/App";
import i18n from "../../../shared/i18n";
import { renderWithProviders, testUser } from "../../../test/render";
import { Audit } from "./Audit";

const event = {
  id: 1,
  actor: "00000000-0000-4000-8000-000000000001",
  actor_role: "admin",
  action: "view",
  target_type: "household",
  target_id: "abc",
  metadata: {},
  created_at: "2026-10-31T16:00:00Z",
};

describe("Audit search", () => {
  it.each([
    { metadata: { outcome: "approved" }, expected: "Approuvé" },
    { metadata: { outcome: "rejected" }, expected: "Refusé" },
    { metadata: {}, expected: "—" },
    { metadata: null, expected: "—" },
    { metadata: "unexpected", expected: "—" },
    { metadata: { outcome: 42 }, expected: "—" },
  ])("renders outcome safely for $metadata", async ({ metadata, expected }) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json({
          count: 1,
          next: null,
          previous: null,
          results: [{ ...event, metadata }],
        }),
      ),
    );
    renderWithProviders(<Audit />);
    expect(await screen.findByRole("cell", { name: expected })).toBeInTheDocument();
  });

  it("submits filters and pages through results", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/staff/audit/")) {
        return Response.json({
          count: 2,
          next: url.includes("page=2") ? null : "next",
          previous: url.includes("page=2") ? "previous" : null,
          results: [event],
        });
      }
      return new Response(null, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderWithProviders(<Audit />);
    expect(await screen.findByText("Ménage: abc")).toBeInTheDocument();
    await user.type(
      screen.getByLabelText("Identifiant du ménage"),
      "00000000-0000-4000-8000-000000000001",
    );
    await user.click(screen.getByRole("button", { name: "Rechercher" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("household=00000000-0000-4000-8000-000000000001"),
        expect.anything(),
      ),
    );
    await user.click(await screen.findByRole("button", { name: "Suivant" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("page=2"), expect.anything()),
    );
    expect(await screen.findByText("Page 2")).toBeInTheDocument();
  });

  it("restricts the route to admins", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/api/me/")) return Response.json(testUser("intake_worker"));
      return new Response(null, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWithProviders(<App />, { route: "/staff/audit" });
    await screen.findByRole("heading", { name: "Foyers" });
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).includes("/api/staff/audit/")),
    ).toBe(false);
  });

  it("loads the audit screen for an admin", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input).endsWith("/api/me/")) return Response.json(testUser("admin"));
        if (String(input).includes("/api/staff/audit/")) {
          return Response.json({ count: 1, next: null, previous: null, results: [event] });
        }
        return new Response(null, { status: 404 });
      }),
    );
    renderWithProviders(<App />, { route: "/staff/audit" });
    expect(await screen.findByText("Ménage: abc")).toBeInTheDocument();
  });

  it("shows an error when the API fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));
    renderWithProviders(<Audit />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("shows an error and allows retry when the results array is invalid", async () => {
    let auditRequests = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (!String(input).includes("/api/staff/audit/")) return new Response(null, { status: 401 });
      auditRequests += 1;
      return Response.json({
        count: 1,
        next: null,
        previous: null,
        results: auditRequests === 1 ? null : [event],
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWithProviders(<Audit />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: /réessayer/i }));
    expect(await screen.findByText("Ménage: abc")).toBeInTheDocument();
  });

  it("validates IDs and date ranges and supports English", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/api/me/")) return new Response(null, { status: 401 });
      return Response.json({
        count: 0,
        next: null,
        previous: null,
        results: [],
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderWithProviders(<Audit />);
    await screen.findByText("Aucun événement trouvé");
    await act(async () => {
      await i18n.changeLanguage("en");
    });
    await user.type(screen.getByLabelText("Household ID"), "invalid");
    await user.click(screen.getByRole("button", { name: "Search" }));
    expect(screen.getByText("Enter a valid ID.")).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Household ID"));
    fireEvent.change(screen.getByLabelText("From date"), { target: { value: "2026-11-02" } });
    fireEvent.change(screen.getByLabelText("To date"), { target: { value: "2026-11-01" } });
    await user.click(screen.getByRole("button", { name: "Search" }));
    expect(screen.getByText("The end date must not be before the start date.")).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).includes("/api/staff/audit/")),
    ).toHaveLength(1);
  });
});
