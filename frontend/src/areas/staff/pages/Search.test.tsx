// AI contribution: 50% or more AI-generated
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../../../app/App";
import type { Role } from "../../../features/accounts/currentUser";
import i18n from "../../../shared/i18n";
import { searchFile, searchPage } from "../../../test/householdSearch";
import { expectNoAxeViolations, renderWithProviders, testUser } from "../../../test/render";
import { Search } from "./Search";

function mockApi(
  handler: (url: URL, init?: RequestInit) => Response | Promise<Response> = () =>
    Response.json(searchPage()),
  role: Role | "signed-out" = "intake_worker",
  accessStatus?: number,
) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://iris.local");
    if (url.pathname === "/api/me/") {
      return role === "signed-out"
        ? new Response(null, { status: 401 })
        : Response.json(testUser(role));
    }
    if (url.pathname === "/api/staff/households/" && init?.method === "HEAD") {
      const allowed = role === "intake_worker" || role === "admin";
      return new Response(null, { status: accessStatus ?? (allowed ? 200 : 403) });
    }
    if (url.pathname === "/api/staff/households/") return handler(url, init);
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function searchInput(value: string) {
  fireEvent.change(screen.getByRole("searchbox"), { target: { value } });
}

function renderSearch() {
  return renderWithProviders(
    <main>
      <Search />
    </main>,
  );
}

afterEach(() => vi.useRealTimers());

describe("staff household search timing and translations", () => {
  it("uses shared success and danger badges for household results", async () => {
    mockApi(() =>
      Response.json(
        searchPage({
          count: 2,
          results: [
            searchFile({ status: "approved" }),
            searchFile({ id: "00000000-0000-4000-8000-000000000064", status: "suspended" }),
          ],
        }),
      ),
    );
    renderSearch();
    searchInput("exemple");
    expect((await screen.findByText("Approuvé")).closest("[data-tone]")).toHaveAttribute(
      "data-tone",
      "success",
    );
    expect(screen.getByText("Suspendu").closest("[data-tone]")).toHaveAttribute(
      "data-tone",
      "danger",
    );
  });

  it("waits 300 ms and sends only the latest input", async () => {
    const handler = vi.fn((url: URL) => {
      expect(url.searchParams.get("page")).toBe("1");
      return Response.json(searchPage());
    });
    mockApi(handler);
    vi.useFakeTimers();
    renderSearch();
    expect(handler).not.toHaveBeenCalled();
    searchInput("elo");
    await act(() => vi.advanceTimersByTimeAsync(200));
    searchInput("elodie");
    await act(() => vi.advanceTimersByTimeAsync(299));
    expect(handler).not.toHaveBeenCalled();
    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler.mock.calls[0]?.[0].searchParams.get("q")).toBe("elodie");
  });

  it.each(["fr", "en"])("shows the search, results and status in %s", async (language) => {
    await i18n.changeLanguage(language);
    mockApi();
    renderSearch();
    const label = language === "fr" ? "Rechercher un foyer" : "Find a household";
    expect(screen.getByRole("searchbox", { name: label })).toHaveAttribute("maxlength", "254");
    searchInput("elodie");
    expect(await screen.findByText("Élodie Exemple")).toBeInTheDocument();
    expect(screen.getByText(language === "fr" ? "Brouillon" : "Draft")).toBeInTheDocument();
    expect(
      screen.getByText(language === "fr" ? "1 foyer trouvé" : "1 household found"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: language === "fr" ? "Reprendre l’inscription" : "Resume registration",
      }),
    ).toHaveAttribute("href", `/staff/walk-in/${searchFile().id}`);
  });
});

describe("staff household search clearing and cancellation", () => {
  it("clears results immediately and never searches blank input", async () => {
    const handler = vi.fn(() => Response.json(searchPage()));
    mockApi(handler);
    renderSearch();
    searchInput("elodie");
    await screen.findByText("Élodie Exemple");
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: "Effacer la recherche" }));
    expect(screen.queryByText("Élodie Exemple")).not.toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(350));
    expect(handler).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Commencez à saisir pour rechercher un foyer")).toBeInTheDocument();
  });

  it("cancels old requests and keeps a late response from replacing the current results", async () => {
    let completeOld!: (response: Response) => void;
    let oldSignal: AbortSignal | undefined;
    mockApi((url, init) => {
      if (url.searchParams.get("q") === "elodie") {
        oldSignal = init?.signal ?? undefined;
        return new Promise<Response>((resolve) => {
          completeOld = resolve;
        });
      }
      return Response.json(searchPage({ results: [searchFile({ first_name: "Zoé" })] }));
    });
    renderSearch();
    searchInput("elodie");
    await waitFor(() => expect(oldSignal).toBeDefined());
    searchInput("zoe");
    expect(await screen.findByText("Zoé Exemple")).toBeInTheDocument();
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => completeOld(Response.json(searchPage())));
    expect(screen.queryByText("Élodie Exemple")).not.toBeInTheDocument();
    expect(screen.getByText("Zoé Exemple")).toBeInTheDocument();
  });
});

describe("staff household search pagination", () => {
  it("paginates and resets to page one when the input changes", async () => {
    const handler = vi.fn((url: URL) => {
      const second = url.searchParams.get("page") === "2";
      return Response.json(
        searchPage({
          count: 21,
          next: second ? null : "next",
          previous: second ? "previous" : null,
          results: [searchFile({ first_name: second ? "Zoé" : "Élodie" })],
        }),
      );
    });
    mockApi(handler);
    renderSearch();
    searchInput("Exemple");
    await screen.findByText("Élodie Exemple");
    expect(screen.getByRole("button", { name: "Précédent" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Suivant" }));
    await screen.findByText("Zoé Exemple");
    expect(screen.getByText("Page 2")).toBeInTheDocument();
    searchInput("nouveau");
    expect(screen.queryByText("Zoé Exemple")).not.toBeInTheDocument();
    await screen.findByText("Élodie Exemple");
    expect(handler.mock.calls.at(-1)?.[0].searchParams.get("page")).toBe("1");
  });
});

describe("staff household search empty and error states", () => {
  it("shows an empty state and supports files without a holder or email", async () => {
    mockApi((url) =>
      Response.json(
        url.searchParams.get("q") === "missing"
          ? searchPage({ count: 0, results: [] })
          : searchPage({
              results: [
                searchFile({ first_name: null, last_name: null, email: null, member_number: null }),
              ],
            }),
      ),
    );
    renderSearch();
    searchInput("missing");
    await screen.findByRole("heading", { name: "Aucun foyer trouvé" });
    searchInput("legacy");
    await screen.findByRole("heading", { name: "Nom non renseigné" });
    expect(screen.getByText("Numéro de membre non attribué")).toBeInTheDocument();
    expect(screen.getByText("Non renseigné")).toBeInTheDocument();
  });

  it("retries a failed request without automatic retries", async () => {
    let requests = 0;
    mockApi(() =>
      ++requests === 1 ? new Response(null, { status: 500 }) : Response.json(searchPage()),
    );
    renderSearch();
    searchInput("elodie");
    await screen.findByRole("alert");
    expect(requests).toBe(1);
    fireEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    await screen.findByText("Élodie Exemple");
    expect(requests).toBe(2);
  });
});

describe("staff household search permissions", () => {
  it("expires a cached signed-in profile when the access API returns 401", async () => {
    const fetchMock = mockApi(undefined, "intake_worker", 401);
    renderWithProviders(<App />, { route: "/staff/households" });
    expect(await screen.findByRole("heading", { name: "Connexion" })).toBeInTheDocument();
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([, options]) => options?.method === "HEAD")).toHaveLength(
      1,
    );
  });

  it("withholds search when the API refuses a user whose role previously allowed it", async () => {
    const handler = vi.fn(() => Response.json(searchPage()));
    mockApi(handler, "admin", 403);
    renderWithProviders(<App />, { route: "/staff/households" });
    await screen.findByRole("heading", { name: "Accès refusé" });
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
    expect(handler).not.toHaveBeenCalled();
  });

  it("uses the API authorization response instead of a frontend role list", async () => {
    mockApi(undefined, "beneficiary", 200);
    renderWithProviders(<App />, { route: "/staff/households" });
    expect(await screen.findByRole("searchbox")).toBeInTheDocument();
  });

  it("fails closed and lets the user retry when the access check is unavailable", async () => {
    const fetchMock = mockApi(undefined, "intake_worker", 500);
    renderWithProviders(<App />, { route: "/staff/households" });
    await screen.findByRole("alert");
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
    const before = fetchMock.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(before));
  });

  it.each([401, 403])("explains refused HTTP %s and links back to sign-in", async (status) => {
    mockApi(() => new Response(null, { status }));
    renderSearch();
    searchInput("elodie");
    await screen.findByRole("heading", { name: "Accès refusé" });
    expect(screen.getByRole("link", { name: "Se reconnecter" })).toHaveAttribute(
      "href",
      "/sign-in",
    );
  });

  it.each(["admin", "intake_worker"] as const)(
    "allows the existing staff route for %s",
    async (role) => {
      mockApi(undefined, role);
      renderWithProviders(<App />, { route: "/staff/households" });
      await screen.findByRole("searchbox");
      searchInput("elodie");
      expect(await screen.findByText("Élodie Exemple")).toBeInTheDocument();
    },
  );

  it.each(["beneficiary", "store_staff", "store_manager", "signed-out"] as const)(
    "keeps %s out of staff search",
    async (role) => {
      const handler = vi.fn(() => Response.json(searchPage()));
      mockApi(handler, role);
      renderWithProviders(<App />, { route: "/staff/households" });
      await screen.findByRole("heading", {
        name:
          role === "beneficiary" ? "Accueil" : role === "signed-out" ? "Connexion" : "Aujourd'hui",
      });
      expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
      expect(handler).not.toHaveBeenCalled();
    },
  );
});

describe("staff household search accessibility", () => {
  it("passes accessibility checks for the result structure", async () => {
    mockApi();
    const { container } = renderSearch();
    searchInput("elodie");
    await screen.findByText("Élodie Exemple");
    await expectNoAxeViolations(container);
  });

  it("clears by keyboard and returns focus to the search field", async () => {
    mockApi();
    const user = userEvent.setup();
    renderSearch();
    const input = screen.getByRole("searchbox");
    await user.click(input);
    await user.type(input, "elodie");
    await screen.findByText("Élodie Exemple");
    await user.tab();
    expect(screen.getByRole("button", { name: "Effacer la recherche" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(input).toHaveValue("");
    expect(input).toHaveFocus();
  });
});

describe("staff household search server actions", () => {
  it.each([
    ["walk_in", "draft", false],
    ["online", "approved", true],
  ] as const)("renders the API resume flag for %s/%s: %s", async (channel, status, canResume) => {
    mockApi(() =>
      Response.json(
        searchPage({ results: [searchFile({ channel, status, can_resume: canResume })] }),
      ),
    );
    renderSearch();
    searchInput("elodie");
    await screen.findByText("Élodie Exemple");
    const link = screen.queryByRole("link", { name: "Reprendre l’inscription" });
    if (canResume) {
      expect(link).toHaveAttribute("href", `/staff/walk-in/${searchFile().id}`);
    } else {
      expect(link).not.toBeInTheDocument();
    }
  });
});
