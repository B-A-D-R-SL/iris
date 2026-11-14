// AI contribution: 50% or more AI-generated
// Shared fakes and steps for the walk-in Notices screen tests (US-18).
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, vi } from "vitest";

import App from "../app/App";
import type { RecordedNotice, WalkInDecision } from "../features/households/noticeApi";
import type { WalkInDraft } from "../features/households/walkInApi";
import { renderWithProviders, testUser } from "./render";

export const ID = "6f1c2c1e-0000-4000-8000-000000000018";
export const ROUTE = `/staff/walk-in/${ID}/notices`;
export const NOTICES_URL = `/api/staff/households/${ID}/notices/`;
export const APPROVE_URL = `/api/staff/households/${ID}/approve/`;
export const SUBMIT_URL = `/api/staff/households/${ID}/submit/`;
export const SUMMARY_URL = `/api/staff/households/${ID}/decision-summary/`;

/** A walk-in draft with one adult holder and one child (generated data only). */
export function draft(status = "draft", statusReason = ""): WalkInDraft {
  return {
    id: ID,
    channel: "walk_in",
    status,
    status_reason: statusReason,
    member_number: null,
    expires_at: null,
    allowed_actions: [],
    reason_max_length: 500,
    email: null,
    preferred_language: "fr",
    phone: "+15145550156",
    street_number: "100",
    street_name: "rue Exemple",
    unit: "",
    city: "Montréal",
    postal_code: "H2X 1Y4",
    identity_checked_in_person: true,
    consent_data_processing_at: "2026-11-02T14:05:00Z",
    consent_text_version: "2026-11-v1",
    members: [
      {
        id: "m1",
        first_name: "Nadia",
        last_name: "Démo",
        date_of_birth: "1990-04-12",
        relation: "holder",
      },
      {
        id: "m2",
        first_name: "Léo",
        last_name: "Démo",
        date_of_birth: "2015-06-01",
        relation: "child",
      },
    ],
    created_by_email: "sophie@example.org",
    created_at: "2026-11-02T14:05:00Z",
    updated_at: "2026-11-02T14:05:00Z",
    verified_by_email: "sophie@example.org",
    verified_at: "2026-11-02T14:05:00Z",
  } as WalkInDraft;
}

export function recorded(overrides: Partial<RecordedNotice> = {}): RecordedNotice {
  return {
    id: "n1",
    member: "m1",
    status: "current",
    source: "walk_in",
    tax_year: 2025,
    total_income_cents: 1_850_000,
    name_on_notice: "Nadia Démo",
    postal_code_on_notice: "H2X 1Y4",
    notice_date: "2026-04-30",
    seen_in_person: true,
    did_not_file_reason: "",
    has_file: true,
    created_at: "2026-11-10T15:00:00Z",
    ...overrides,
  } as RecordedNotice;
}

/** The decision as the approve endpoint returns it. */
export function decision(overrides: Partial<WalkInDecision> = {}): WalkInDecision {
  return {
    id: ID,
    status: "approved",
    status_reason: "",
    approved_at: "2026-11-10T14:00:00Z",
    expires_at: "2027-11-10T14:00:00Z",
    invitation_not_sent: false,
    ...overrides,
  };
}

/** Records "did not file" for Nadia so the file is ready for a decision. */
export async function recordDidNotFile() {
  const nadia = within(card("Nadia Démo"));
  await userEvent.click(nadia.getByRole("checkbox", { name: /n'a pas produit de déclaration/ }));
  await userEvent.type(nadia.getByLabelText("Expliquez pourquoi"), "Aucun revenu en 2025");
  await userEvent.click(nadia.getByRole("button", { name: "Enregistrer l'avis" }));
  await waitFor(() => expect(within(summary()).getByText("N'a pas produit")).toBeVisible());
}

/** What the API works out for this file: one adult and one child, so a household of two. */
export function summaryFor(stored: RecordedNotice[]) {
  const mine = stored.find((entry) => entry.member === "m1");
  const review = Boolean(mine && (mine.did_not_file_reason || !mine.seen_in_person));
  const decided = Boolean(mine) && !review;
  const eligible = decided ? (mine?.total_income_cents ?? 0) <= 3_000_000 : null;
  return {
    household_size: 2,
    adult_count: 1,
    ready_for_decision: Boolean(mine),
    will_go_to_review: review,
    total_income_cents: decided ? (mine?.total_income_cents ?? null) : null,
    threshold_cents: 3_000_000,
    eligible,
    // Only a file that approval would approve has a length and an end date.
    approved_months: eligible ? 12 : null,
    valid_until: eligible ? "2027-11-14T12:00:00Z" : null,
    adult_member_ids: ["m1"],
    notice_rules: {
      max_bytes: 10 * 1024 * 1024,
      earliest_tax_year: 2000,
      reason_max_length: 500,
      max_income_cents: 50_000_000,
    },
  };
}

/** Fakes /api/me/, the file read, the notice list and record, and the submit and approve endpoints. */
export function mockApi(
  record: () => Response = () => Response.json(recorded(), { status: 201 }),
  approve: () => Response = () => Response.json(decision()),
  saved: RecordedNotice[] = [],
  file: { status?: string; statusReason?: string; submitTo?: string; expiresAt?: string } = {},
) {
  // The file's status, as the server would report it after a submission.
  const state = { status: file.status ?? "draft", reason: file.statusReason ?? "" };
  let stored = [...saved];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = input instanceof Request ? input.url : String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/me/")) return Response.json(testUser("intake_worker"));
    if (url.endsWith(`/api/staff/households/${ID}/`) && method === "GET") {
      return Response.json({
        ...draft(state.status, state.reason),
        expires_at: file.expiresAt ?? null,
      });
    }
    if (url.endsWith(SUBMIT_URL) && method === "POST") {
      state.status = file.submitTo ?? "submitted";
      state.reason = state.status === "review_required" ? "POSSIBLE_DUPLICATE" : "";
      return Response.json({
        id: ID,
        status: state.status,
        status_reason: state.reason,
        submitted_at: "2026-11-10T14:00:00Z",
      });
    }
    if (url.endsWith(NOTICES_URL) && method === "GET") return Response.json(stored);
    if (url.endsWith(NOTICES_URL) && method === "POST") {
      const response = record();
      // Like the server, keep what was recorded for the next read.
      if (response.ok) {
        const notice = (await response.clone().json()) as RecordedNotice;
        stored = [...stored.filter((entry) => entry.member !== notice.member), notice];
      }
      return response;
    }
    if (url.endsWith(APPROVE_URL) && method === "POST") return approve();
    if (url.endsWith(SUMMARY_URL) && method === "GET") return Response.json(summaryFor(stored));
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function sentForm(fetchMock: ReturnType<typeof mockApi>): FormData {
  const call = fetchMock.mock.calls.find(
    ([input, init]) => String(input).endsWith(NOTICES_URL) && init?.method === "POST",
  );
  if (!call) throw new Error("No notice was sent");
  return call[1]?.body as FormData;
}

// The card is titled "Adulte 1 · name (personne responsable)": match on the name.
export const card = (name: string) => screen.getByRole("region", { name: new RegExp(name) });
export const summary = () => screen.getByRole("region", { name: "Résumé pour la décision" });

/** Every notice is in: submit the draft (duplicate check) so approval is offered. */
export async function submitFile() {
  await userEvent.click(screen.getByRole("button", { name: "Soumettre le dossier" }));
  await screen.findByRole("button", { name: /Approuver (le dossier|pour 12 mois)/ });
}

/** Approval is final: it asks first (Figma W6.3 S26), then the server decides. */
export async function approve() {
  await userEvent.click(
    screen.getByRole("button", { name: /Approuver (le dossier|pour 12 mois)/ }),
  );
  await userEvent.click(await screen.findByRole("button", { name: "Confirmer l'approbation" }));
}

export async function openPage() {
  renderWithProviders(<App />, { route: ROUTE });
  await screen.findByRole("heading", { level: 1, name: "Avis et décision · Nadia Démo" });
  // The numbers come from the API, so wait for them before acting.
  await screen.findByText("Taille du foyer");
}
