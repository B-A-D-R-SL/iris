// AI contribution: 50% or more AI-generated
import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it } from "vitest";

import i18n from "../../../shared/i18n";
import { expectNoAxeViolations } from "../../../test/render";
import {
  CATEGORIES,
  chooseCategory,
  fillRequiredFields,
  mockApi,
  publish,
  refused,
  renderForm,
  setupListingClock,
} from "../../../test/listingPosting";

setupListingClock();

beforeEach(async () => {
  await act(async () => {
    await i18n.changeLanguage("fr");
  });
});

it("Listing safety checks (US-34) offers only the categories the server allows, so prohibited ones cannot be chosen", async () => {
  // The server left out a prohibited category: only bakery comes back.
  const fetchMock = mockApi({ categories: () => Response.json([CATEGORIES[0]]) });
  await renderForm();
  await userEvent.click(screen.getByRole("button", { name: "Catégorie" }));
  const sheet = await screen.findByRole("dialog", { name: "Catégorie" });

  expect(within(sheet).getByRole("radio", { name: "Boulangerie" })).toBeVisible();
  expect(within(sheet).queryByRole("radio", { name: "Hygiène personnelle" })).toBeNull();
  const urls = fetchMock.mock.calls.map(([input]) => String(input));
  expect(urls).toContain("/api/store/listings/categories/");
  expect(urls).not.toContain("/api/categories/");
});

// Full form interactions (plus axe in French) can exceed the 5s default on VMs.
it("Listing safety checks (US-34) shows each safety refusal under its field, in French", async () => {
  mockApi({
    post: refused({
      category: ["Cette catégorie ne peut pas être publiée. Choisissez-en une autre."],
      best_before: ["Choisissez le 12 nov. 2026 ou après (fin de la cueillette)."],
      safe_and_allowed: ["Cochez cette case pour publier."],
    }),
  });
  const { container } = await renderForm();
  await fillRequiredFields();
  await chooseCategory("Boulangerie");
  await userEvent.type(screen.getByLabelText("Meilleur avant"), "2026-11-11");
  await publish();

  expect(await screen.findByText("Vérifiez 3 champs")).toBeVisible();
  const category = screen.getByRole("button", { name: "Catégorie" });
  expect(category).toHaveAccessibleDescription(
    "Cette catégorie ne peut pas être publiée. Choisissez-en une autre.",
  );
  expect(screen.getByLabelText("Meilleur avant")).toHaveAccessibleDescription(
    expect.stringContaining("Choisissez le 12 nov. 2026 ou après (fin de la cueillette)."),
  );
  expect(screen.getByText("Cochez cette case pour publier.")).toBeVisible();
  await expectNoAxeViolations(container);
}, 15000);

it("Listing safety checks (US-34) shows the server's English safety messages after switching language", async () => {
  const fetchMock = mockApi({
    post: refused({
      best_before: ["Enter a best-before date. It is required for food."],
    }),
  });
  await renderForm();
  await act(async () => {
    await i18n.changeLanguage("en");
  });
  await userEvent.type(screen.getByLabelText("Title"), "Day-old bread");
  await userEvent.click(screen.getByRole("button", { name: "Category" }));
  const sheet = await screen.findByRole("dialog", { name: "Category" });
  await userEvent.click(within(sheet).getByRole("radio", { name: "Bakery" }));
  await userEvent.type(screen.getByLabelText("Best before"), "2026-11-14");
  await userEvent.click(screen.getByRole("checkbox", { name: /safe and allowed/ }));
  await userEvent.click(screen.getByRole("button", { name: "Publish the listing" }));

  expect(
    await screen.findByText("Enter a best-before date. It is required for food."),
  ).toBeVisible();
  const call = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  expect(call?.[1]?.headers).toMatchObject({ "Accept-Language": "en" });
}, 15000);

it("Listing safety checks (US-34) shows the prohibited-items links as unavailable placeholders", async () => {
  mockApi();
  await renderForm();
  const link = screen.getByRole("button", { name: "Voir la liste des produits interdits" });
  expect(link).toHaveAttribute("aria-disabled", "true");
  await userEvent.click(link);
  // Nothing opens and the worker stays on the form.
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Publier l'offre" })).toBeVisible();

  await userEvent.click(screen.getByRole("button", { name: "Catégorie" }));
  const sheet = await screen.findByRole("dialog", { name: "Catégorie" });
  expect(within(sheet).getByRole("button", { name: "Voir la liste" })).toHaveAttribute(
    "aria-disabled",
    "true",
  );

  await act(async () => {
    await i18n.changeLanguage("en");
  });
  expect(screen.getByRole("button", { name: "See the list of prohibited items" })).toBeVisible();
});
