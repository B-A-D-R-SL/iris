// AI contribution: 50% or more AI-generated
/** Fictional search responses shared by API and component tests. */
import type { HouseholdSearchPage, HouseholdSearchResult } from "../features/households/searchApi";

export function searchFile(overrides: Partial<HouseholdSearchResult> = {}): HouseholdSearchResult {
  return {
    id: "00000000-0000-4000-8000-000000000063",
    first_name: "Élodie",
    last_name: "Exemple",
    member_number: "IR-000123",
    status: "draft",
    channel: "walk_in",
    email: "elodie@example.test",
    phone: "+15145550123",
    street_number: "123",
    street_name: "rue Exemple",
    unit: "4",
    city: "Montréal",
    postal_code: "H0H 0H0",
    ...overrides,
  };
}

export function searchPage(overrides: Partial<HouseholdSearchPage> = {}): HouseholdSearchPage {
  return { count: 1, next: null, previous: null, results: [searchFile()], ...overrides };
}
