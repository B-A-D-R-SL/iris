// AI contribution: 50% or more AI-generated
import { screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import {
  fillRequiredFields,
  mockApi,
  publish,
  renderForm,
  setupListingClock,
} from "../../../test/listingPosting";

setupListingClock();

/** The JSON entries the shared logger wrote to one console channel. */
const entries = (spy: { mock: { calls: unknown[][] } }) =>
  spy.mock.calls.map(([line]) => JSON.parse(String(line)) as Record<string, unknown>);

afterEach(() => vi.restoreAllMocks());

it("Failed post log (FIX-12) logs a server failure as an error with its status code only", async () => {
  const error = vi.spyOn(console, "error").mockImplementation(() => {});
  mockApi({
    post: () =>
      Response.json(
        { code: "posting_unavailable", message: "Indisponible.", fields: {} },
        { status: 503 },
      ),
  });
  await renderForm();
  await fillRequiredFields();
  await publish();
  await screen.findByText("L'offre n'a pas été publiée");

  expect(entries(error)).toEqual([
    {
      timestamp: expect.any(String),
      level: "ERROR",
      event: "listing_post_failed",
      status_code: 503,
    },
  ]);
});

it("Failed post log (FIX-12) logs a refused post as a warning, without anything the worker typed", async () => {
  const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
  mockApi({
    post: () =>
      Response.json(
        { code: "validation_error", message: "Vérifiez.", fields: { title: ["Refusé."] } },
        { status: 400 },
      ),
  });
  await renderForm();
  await fillRequiredFields();
  await publish();
  await screen.findByText("Refusé.");

  expect(entries(warn)).toEqual([
    {
      timestamp: expect.any(String),
      level: "WARNING",
      event: "listing_post_failed",
      status_code: 400,
    },
  ]);
  expect(JSON.stringify(warn.mock.calls)).not.toContain("Pains de la veille");
});

it("Failed post log (FIX-12) logs a 201 whose answer cannot be read as an error with its status code", async () => {
  const error = vi.spyOn(console, "error").mockImplementation(() => {});
  mockApi({ post: () => new Response("{not json", { status: 201 }) });
  await renderForm();
  await fillRequiredFields();
  await publish();
  await screen.findByRole("alert");

  expect(entries(error)).toEqual([
    {
      timestamp: expect.any(String),
      level: "ERROR",
      event: "listing_post_failed",
      status_code: 201,
    },
  ]);
});

it("Failed post log (FIX-12) logs a lost connection as an error with no status code", async () => {
  const error = vi.spyOn(console, "error").mockImplementation(() => {});
  const fetchMock = mockApi();
  const answer = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (input, init) => {
    if (init?.method === "POST") throw new TypeError("Failed to fetch");
    return answer(input, init);
  });
  await renderForm();
  await fillRequiredFields();
  await publish();
  await screen.findByText("Vérifiez votre connexion Internet, puis réessayez.");

  expect(entries(error)).toEqual([
    {
      timestamp: expect.any(String),
      level: "ERROR",
      event: "listing_post_failed",
      status_code: null,
    },
  ]);
});
