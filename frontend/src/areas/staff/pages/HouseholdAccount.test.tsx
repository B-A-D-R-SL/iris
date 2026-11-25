// AI contribution: 50% or more AI-generated
import { QueryClient } from "@tanstack/react-query";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import type { HouseholdAccount } from "../../../features/households/statusApi";
import i18n from "../../../shared/i18n";
import { expectNoAxeViolations, renderWithProviders } from "../../../test/render";
import { HouseholdAccountCard } from "./HouseholdAccount";

const id = "00000000-0000-4000-8000-000000000093";
const email = "holder@example.test";

function state(
  status: HouseholdAccount["status"],
  overrides: Partial<HouseholdAccount> = {},
): HouseholdAccount {
  return {
    status,
    reason: "",
    account_first_name: null,
    account_last_name: null,
    ...overrides,
  };
}

const linkable = state("can_link", { account_first_name: "Sam", account_last_name: "Exemple" });

const reloadKey = ["staff-household", id];

/** Render the card; `reloaded` records each reload of the file's query. */
function show(account: HouseholdAccount) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const reloaded = vi.spyOn(queryClient, "invalidateQueries");
  const view = renderWithProviders(
    <HouseholdAccountCard
      householdId={id}
      email={email}
      holderName="Samira Example"
      account={account}
      reloadKey={reloadKey}
    />,
    { queryClient },
  );
  return { ...view, reloaded };
}

function answer(response: Response) {
  const fetchMock = vi.fn(async () => response.clone());
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});

it("Household account card (US-93) says the account is linked without promising access a suspended file lacks", () => {
  show(state("linked"));
  expect(screen.getByText(/account is linked to this file/)).toBeVisible();
  // The page also shows suspended and expired files: access depends on the status.
  expect(screen.queryByText(/browse and reserve/)).not.toBeInTheDocument();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});

it("Household account card (US-93) says an invitation leads to access only while the file is approved", () => {
  show(state("invited"));
  expect(screen.getByText(/password was sent to holder@example.test/)).toBeVisible();
  // The file can be suspended or expire before the password is chosen.
  expect(screen.getByText(/while the file is approved/)).toBeVisible();
});

it("Household account card (US-93) says a counter-only file needs no account", () => {
  show(state("no_email"));
  expect(screen.getByText(/served at the counter/)).toBeVisible();
});

it("Household account card (US-93) shows nothing for a file that is not an approved walk-in", () => {
  show(state("not_applicable"));
  expect(screen.queryByRole("heading", { name: "Iris account" })).not.toBeInTheDocument();
});

it("Household account card (US-93) explains why an existing account cannot be linked", () => {
  show(state("cannot_link", { reason: "has_household" }));
  expect(screen.getByText(/already linked to another household/)).toBeVisible();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});

it("Household account card (US-93) keeps Link disabled until the ID check is ticked", async () => {
  show(linkable);
  await userEvent.click(screen.getByRole("button", { name: "Link this account" }));
  expect(await screen.findByText("Holder on the file: Samira Example")).toBeVisible();
  expect(screen.getByText("Name on the account: Sam Exemple")).toBeVisible();
  const confirm = screen.getAllByRole("button", { name: "Link this account" }).at(-1)!;
  expect(confirm).toBeDisabled();
  await userEvent.click(screen.getByRole("checkbox", { name: /I checked the person's ID/ }));
  expect(confirm).toBeEnabled();
});

it("Household account card (US-93) links with the ID confirmation and reports success", async () => {
  const fetchMock = answer(Response.json(state("linked")));
  const { reloaded } = show(linkable);
  await userEvent.click(screen.getByRole("button", { name: "Link this account" }));
  await userEvent.click(screen.getByRole("checkbox", { name: /I checked the person's ID/ }));
  await userEvent.click(screen.getAllByRole("button", { name: "Link this account" }).at(-1)!);
  expect(await screen.findByText(/The account is linked/)).toBeVisible();
  expect(fetchMock).toHaveBeenCalledWith(
    `/api/staff/households/${id}/link-account/`,
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ identity_confirmed: true }),
    }),
  );
  expect(reloaded).toHaveBeenCalledWith({ queryKey: reloadKey });
});

it("Household account card (US-93) shows the server's refusal message", async () => {
  answer(
    Response.json(
      {
        message: "Check the highlighted fields.",
        fields: { non_field_errors: ["This account is already linked to another household."] },
      },
      { status: 400 },
    ),
  );
  const { reloaded } = show(linkable);
  await userEvent.click(screen.getByRole("button", { name: "Link this account" }));
  await userEvent.click(screen.getByRole("checkbox", { name: /I checked the person's ID/ }));
  await userEvent.click(screen.getAllByRole("button", { name: "Link this account" }).at(-1)!);
  expect(
    await screen.findByText("This account is already linked to another household."),
  ).toBeVisible();
  expect(reloaded).not.toHaveBeenCalled();
});

it("Household account card (US-93) resends the invitation and says the previous link stops working", async () => {
  const fetchMock = answer(Response.json(state("invited")));
  const { reloaded } = show(state("invited"));
  expect(screen.getByText(/The previous link will stop working/)).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "Send a new invitation" }));
  expect(await screen.findByText(/A new invitation was sent/)).toBeVisible();
  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/staff/households/${id}/resend-invitation/`,
      expect.objectContaining({ method: "POST", body: "{}" }),
    ),
  );
  expect(reloaded).toHaveBeenCalledWith({ queryKey: reloadKey });
});

it("Household account card (US-93) shows a generic failure when the resend is refused without a message", async () => {
  answer(new Response(null, { status: 500 }));
  show(state("invited"));
  await userEvent.click(screen.getByRole("button", { name: "Send a new invitation" }));
  expect(await screen.findByText("The request failed. Try again.")).toBeVisible();
});

it("Household account card (US-93) clears the earlier success when the next action fails", async () => {
  // The first resend works and the second fails; other requests (the current user) get 404.
  const resends = [Response.json(state("invited")), new Response(null, { status: 500 })];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      const resend = url.endsWith("/resend-invitation/") ? resends.shift() : undefined;
      return resend ?? new Response(null, { status: 404 });
    }),
  );
  show(state("invited"));
  await userEvent.click(screen.getByRole("button", { name: "Send a new invitation" }));
  expect(await screen.findByText(/A new invitation was sent/)).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "Send a new invitation" }));
  expect(await screen.findByText("The request failed. Try again.")).toBeVisible();
  expect(screen.queryByText(/A new invitation was sent/)).not.toBeInTheDocument();
});

it("Household account card (US-93) speaks French", async () => {
  await i18n.changeLanguage("fr");
  show(state("invited"));
  expect(screen.getByRole("button", { name: "Envoyer une nouvelle invitation" })).toBeVisible();
});

it("Household account card (US-93) has no accessibility violations", async () => {
  const { container } = show(linkable);
  await expectNoAxeViolations(container);
});
