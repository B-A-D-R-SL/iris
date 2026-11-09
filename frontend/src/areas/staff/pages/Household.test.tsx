// AI contribution: 50% or more AI-generated
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../../shared/i18n";
import { logger } from "../../../shared/logger";
import { expectNoAxeViolations, renderWithProviders, testUser } from "../../../test/render";
import { Household } from "./Household";

const id = "00000000-0000-4000-8000-000000000032";
const page = (
  <Routes>
    <Route path="/staff/households/:id" element={<Household />} />
  </Routes>
);

function household(
  status: "approved" | "suspended" = "approved",
  allowedActions: Array<"suspend" | "reactivate"> = ["suspend"],
) {
  return {
    id,
    member_number: "IR-000032",
    status,
    status_reason: status === "suspended" ? "Safety review" : "",
    email: "holder@example.test",
    phone: "+15145550101",
    preferred_language: "en",
    expires_at: "2027-11-09T12:00:00Z",
    allowed_actions: allowedActions,
    members: [
      {
        id: "00000000-0000-4000-8000-000000000033",
        first_name: "Samira",
        last_name: "Example",
        relation: "holder",
      },
    ],
  };
}

function mockApi(role: "admin" | "intake_worker") {
  let file = household("approved", role === "admin" ? ["suspend"] : []);
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (url.endsWith("/api/me/")) return Response.json(testUser(role));
    if (url === `/api/staff/households/${id}/` && !init?.method) return Response.json(file);
    if (url === `/api/staff/households/${id}/suspend/`) {
      file = household("suspended", ["reactivate"]);
      return Response.json(file);
    }
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("staff household suspension", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("requires a reason and suspends an approved file", async () => {
    const fetchMock = mockApi("admin");
    const { container } = renderWithProviders(page, {
      route: `/staff/households/${id}`,
    });

    expect(await screen.findByRole("heading", { name: "Samira Example" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Suspend file" }));
    const confirm = screen.getAllByRole("button", { name: "Suspend file" }).at(-1)!;
    expect(confirm).toBeDisabled();
    await userEvent.type(screen.getByRole("textbox", { name: /Reason/ }), "Safety review");
    await userEvent.click(confirm);

    expect(await screen.findByText("The household file was suspended.")).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        `/api/staff/households/${id}/suspend/`,
        expect.objectContaining({ body: JSON.stringify({ reason: "Safety review" }) }),
      ),
    );
    await expectNoAxeViolations(container);
  });

  it("renders only the status actions supplied by the backend", async () => {
    mockApi("intake_worker");
    renderWithProviders(page, { route: `/staff/households/${id}` });
    expect(await screen.findByRole("heading", { name: "Samira Example" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Suspend file" })).not.toBeInTheDocument();
  });

  it("logs an invalid household response without logging its body", async () => {
    const warning = vi.spyOn(logger, "warning").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("not-json", { status: 200 })),
    );
    renderWithProviders(page, { route: `/staff/households/${id}` });
    expect(
      await screen.findByRole("heading", { name: "This page could not be shown" }),
    ).toBeInTheDocument();
    expect(warning).toHaveBeenCalledWith("household_status_response_invalid");
  });
});
