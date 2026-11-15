// AI contribution: 50% or more AI-generated
/** Store events in the audit log table (US-14). */
import { act, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { components } from "../../../shared/api/generated";
import i18n from "../../../shared/i18n";
import { renderWithProviders } from "../../../test/render";
import { AuditResultsTable } from "./AuditComponents";

type Event = components["schemas"]["PaginatedAuditEventList"]["results"][number];

function storeEvent(action: Event["action"], metadata: Record<string, unknown>): Event {
  return {
    id: 1,
    actor: "00000000-0000-4000-8000-000000000001",
    actor_role: "admin",
    action,
    target_type: "store",
    target_id: "00000000-0000-4000-8000-0000000000aa",
    metadata,
    created_at: "2026-11-14T15:00:00Z",
  } as Event;
}

describe("AuditResultsTable store events", () => {
  it("shows the changed fields by their labels, in both languages", async () => {
    const events = [storeEvent("update", { fields: "opening_hours,pickup_instructions" })];
    renderWithProviders(<AuditResultsTable events={events} labels={{}} locale="fr-CA" />);

    expect(
      screen.getByText(/champs : Heures d’ouverture, Instructions pour la cueillette/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/opening_hours/)).toBeNull();

    await act(() => i18n.changeLanguage("en"));
    expect(screen.getByText(/fields: Opening hours, Pickup instructions/)).toBeInTheDocument();
    await act(() => i18n.changeLanguage("fr"));
  });

  it("keeps an unknown field name as it is", () => {
    renderWithProviders(
      <AuditResultsTable
        events={[storeEvent("update", { fields: "future_field" })]}
        labels={{}}
        locale="fr-CA"
      />,
    );
    expect(screen.getByText(/champs : future_field/)).toBeInTheDocument();
  });

  it("shows what a deactivation cancelled", () => {
    const events = [
      storeEvent("deactivate", {
        reason: "Fermé",
        listings_cancelled: 2,
        reservations_cancelled: 3,
      }),
    ];
    renderWithProviders(<AuditResultsTable events={events} labels={{}} locale="fr-CA" />);
    expect(screen.getByText(/2 offres et 3 réservations annulées/)).toBeInTheDocument();
  });
});
