// AI contribution: 50% or more AI-generated
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  APPROVE_URL,
  SUBMIT_URL,
  recorded,
  decision,
  mockApi,
  card,
  summary,
  approve,
  openPage,
} from "../../../../test/walkInNotices";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 10, 10, 9, 0));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Walk-in notices: saved files and the decision (US-18, T-03.18.4)", () => {
  it("shows the notices saved earlier, so a reloaded file can still be submitted", async () => {
    mockApi(undefined, undefined, [recorded()]);
    await openPage();

    expect(within(summary()).getByText("Avis enregistré")).toBeVisible();
    expect(within(card("Nadia Démo")).getByText(/2025/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Remplacer cet avis" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Soumettre le dossier" })).toBeEnabled();
  });

  it("disables submission while a saved notice is being replaced", async () => {
    mockApi(undefined, undefined, [recorded()]);
    await openPage();

    await userEvent.click(screen.getByRole("button", { name: "Remplacer cet avis" }));

    expect(screen.getByRole("button", { name: "Soumettre le dossier" })).toBeDisabled();
    expect(screen.getByText(/en cours de remplacement/)).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));

    expect(screen.getByRole("button", { name: "Soumettre le dossier" })).toBeEnabled();
  });

  // rule: BR-DUP-002
  it("submits a draft first, then offers approval", async () => {
    const fetchMock = mockApi(undefined, undefined, [recorded()], { status: "draft" });
    await openPage();

    expect(
      screen.queryByRole("button", { name: /Approuver (le dossier|pour 12 mois)/ }),
    ).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Soumettre le dossier" }));

    expect(
      await screen.findByRole("button", { name: /Approuver (le dossier|pour 12 mois)/ }),
    ).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Soumettre le dossier" })).toBeNull();
    expect(
      fetchMock.mock.calls.some(
        ([input, init]) => String(input).endsWith(SUBMIT_URL) && init?.method === "POST",
      ),
    ).toBe(true);
  });

  // rule: BR-DUP-002
  it("sends a possible duplicate to review and offers no approval", async () => {
    mockApi(undefined, undefined, [recorded()], { status: "draft", submitTo: "review_required" });
    await openPage();

    await userEvent.click(screen.getByRole("button", { name: "Soumettre le dossier" }));

    expect(await screen.findByText("Dossier envoyé en révision")).toBeVisible();
    expect(
      screen.getByText("Un foyer avec la même adresse ou la même personne est déjà inscrit."),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: /Approuver (le dossier|pour 12 mois)/ }),
    ).toBeNull();
  });

  // rule: BR-DOC-007
  it("locks the notices once the file is submitted", async () => {
    mockApi(undefined, undefined, [recorded()], { status: "submitted" });
    await openPage();

    expect(screen.getByText(/n'est plus un brouillon/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Remplacer cet avis" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Soumettre le dossier" })).toBeNull();
    expect(
      screen.getByRole("button", { name: /Approuver (le dossier|pour 12 mois)/ }),
    ).toBeEnabled();
  });

  it("offers nothing once the file is decided", async () => {
    mockApi(undefined, undefined, [recorded()], { status: "approved" });
    await openPage();

    expect(screen.queryByRole("button", { name: "Soumettre le dossier" })).toBeNull();
    expect(
      screen.queryByRole("button", { name: /Approuver (le dossier|pour 12 mois)/ }),
    ).toBeNull();
  });

  it("still shows a saved approval and its date after a reload", async () => {
    mockApi(undefined, undefined, [recorded()], {
      status: "approved",
      expiresAt: "2027-11-10T14:00:00Z",
    });
    await openPage();

    expect(await screen.findByText(/Dossier approuvé jusqu'au 10 novembre 2027/)).toBeVisible();
  });

  it("still shows a saved rejection and its reason after a reload", async () => {
    mockApi(undefined, undefined, [recorded()], {
      status: "rejected",
      statusReason: "INCOME_ABOVE_LICO",
    });
    await openPage();

    expect(await screen.findByText("Dossier refusé")).toBeVisible();
    expect(screen.getByText(/dépasse le seuil de faible revenu/)).toBeVisible();
  });

  // Approving again could not change the outcome, so the screen does not offer it.
  it("shows a file in review with its reasons and no approve action", async () => {
    mockApi(undefined, undefined, [recorded()], {
      status: "review_required",
      statusReason: "POSSIBLE_DUPLICATE",
    });
    await openPage();

    expect(await screen.findByText("Dossier envoyé en révision")).toBeVisible();
    expect(
      screen.queryByRole("button", { name: /Approuver (le dossier|pour 12 mois)/ }),
    ).toBeNull();
  });

  it("asks for confirmation before approving, and approves nothing when cancelled", async () => {
    const fetchMock = mockApi(undefined, undefined, [recorded()], { status: "submitted" });
    await openPage();

    expect(await screen.findByText("Admissible : le revenu est sous le seuil")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Approuver pour 12 mois" }));
    const dialog = await screen.findByRole("dialog", { name: "Approuver ce dossier ?" });
    expect(
      within(dialog).getByText("Le dossier sera valide jusqu'au 14 novembre 2027."),
    ).toBeVisible();
    expect(within(dialog).getByText(/La décision est définitive/)).toBeVisible();
    await userEvent.click(within(dialog).getByRole("button", { name: "Annuler" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(
      fetchMock.mock.calls.some(
        ([input, init]) => String(input).endsWith(APPROVE_URL) && init?.method === "POST",
      ),
    ).toBe(false);
  });

  it("says when the income is above the threshold, before anyone approves", async () => {
    mockApi(undefined, undefined, [recorded({ total_income_cents: 3_500_000 })], {
      status: "submitted",
    });
    await openPage();

    expect(await screen.findByText("Non admissible : le revenu dépasse le seuil")).toBeVisible();
    expect(screen.getByText(/Si vous continuez, le dossier sera refusé/)).toBeVisible();
    // No validity to promise: the button does not mention months.
    expect(screen.getByRole("button", { name: "Approuver le dossier" })).toBeEnabled();
  });

  it("shows the header, the card title and the numbers the API worked out", async () => {
    mockApi(undefined, undefined, [recorded()]);
    await openPage();

    expect(screen.getByText(/Au comptoir · Visite du/)).toBeVisible();
    expect(screen.getByText("Adultes : 1 · Personnes à charge : 1")).toBeVisible();
    expect(
      screen.getByRole("region", { name: "Adulte 1 · Nadia Démo (personne responsable)" }),
    ).toBeVisible();
    const facts = within(summary());
    expect(facts.getByText("Taille du foyer").nextSibling).toHaveTextContent("2");
    expect(facts.getByText("Revenu total du foyer").nextSibling).toHaveTextContent(/18\s?500/);
    expect(facts.getByText("Seuil de faible revenu").nextSibling).toHaveTextContent(/30\s?000/);
  });

  it("writes the colon in the translation: French puts a space before it", async () => {
    mockApi(undefined, undefined, [recorded()]);
    await openPage();

    expect(within(card("Nadia Démo")).getByText(/^Année d'imposition : 2025$/)).toBeVisible();
  });

  it("does not show a zero income when the notice has none", async () => {
    mockApi(undefined, undefined, [recorded({ total_income_cents: null })]);
    await openPage();

    expect(within(card("Nadia Démo")).getByText(/Non fournie/)).toBeVisible();
  });

  it("tells staff when no invitation was sent and offers to link the account", async () => {
    mockApi(undefined, () => Response.json(decision({ invitation_not_sent: true })), [recorded()], {
      status: "submitted",
      account: {
        status: "can_link",
        reason: "",
        account_first_name: "Nadia",
        account_last_name: "Démo",
      },
    });
    await openPage();

    await approve();

    expect(await screen.findByText(/Dossier approuvé jusqu'au/)).toBeVisible();
    expect(screen.getByText(/Aucun courriel n'a été envoyé/)).toBeVisible();
    // US-93: the account is linked only after the ID check, so the note promises no access.
    expect(
      screen.getByText(/Vérifiez la pièce d'identité de la personne, puis liez/),
    ).toBeVisible();
    expect(await screen.findByRole("button", { name: "Lier ce compte" })).toBeVisible();
    expect(screen.queryByText(/ne peut pas encore être lié/)).not.toBeInTheDocument();
    expect(screen.queryByText(/connecter|réinitialiser/)).not.toBeInTheDocument();
  });

  it("says the account is linked once the household chooses a password", async () => {
    mockApi(undefined, undefined, [recorded()], { status: "submitted" });
    await openPage();

    await approve();

    expect(await screen.findByText(/Dossier approuvé jusqu'au/)).toBeVisible();
    expect(screen.getByText(/recevra un lien pour choisir un mot de passe/)).toBeVisible();
    expect(screen.getByText(/Son compte sera alors lié à ce dossier/)).toBeVisible();
  });

  it("explains a file sent to review because an adult has no notice", async () => {
    mockApi(undefined, undefined, [recorded()], {
      status: "review_required",
      statusReason: "NOTICE_MISSING",
    });
    await openPage();

    expect(await screen.findByText(/ni avis ni motif de non-production/)).toBeVisible();
  });
});
