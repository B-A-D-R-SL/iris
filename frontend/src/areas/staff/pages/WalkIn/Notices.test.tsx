// AI contribution: 50% or more AI-generated
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import axe from "axe-core";

import {
  NOTICES_URL,
  APPROVE_URL,
  recorded,
  decision,
  recordDidNotFile,
  mockApi,
  sentForm,
  card,
  summary,
  submitFile,
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

describe("Walk-in notices (US-18, T-03.18.4)", () => {
  it("shows one card per adult, with the phone camera for the notice", async () => {
    mockApi();
    await openPage();

    expect(card("Nadia Démo")).toBeVisible();
    expect(screen.queryByRole("region", { name: "Léo Démo" })).not.toBeInTheDocument();

    const inputs = card("Nadia Démo").querySelectorAll<HTMLInputElement>('input[type="file"]');
    const camera = Array.from(inputs).find((input) => input.getAttribute("capture"));
    expect(camera?.getAttribute("capture")).toBe("environment");
    expect(camera?.accept).toBe("image/*");
    expect(within(summary()).getByText("À enregistrer")).toBeVisible();
    // The shared FileUpload drop zone puts aria-required on a <button> (a known issue in
    // shared/forms, reported to its owner); every other element is checked.
    const results = await axe.run(
      { include: [document.body], exclude: [["[class*='dropZone']"]] },
      { rules: { "color-contrast": { enabled: false } } },
    );
    expect(results.violations.map((violation) => violation.id)).toEqual([]);
  });

  it("checks the card before sending and sends nothing while values are missing", async () => {
    const fetchMock = mockApi();
    await openPage();

    await userEvent.click(screen.getByRole("button", { name: "Enregistrer l'avis" }));

    expect(await screen.findAllByText("Remplissez ce champ.")).not.toHaveLength(0);
    expect(
      fetchMock.mock.calls.some(
        ([input, init]) => String(input).endsWith(NOTICES_URL) && init?.method === "POST",
      ),
    ).toBe(false);
  });

  it("records a photographed notice with the typed values", async () => {
    const fetchMock = mockApi();
    await openPage();
    const nadia = within(card("Nadia Démo"));

    const photo = new File(["jpeg"], "avis.jpg", { type: "image/jpeg" });
    const camera = card("Nadia Démo").querySelector<HTMLInputElement>(
      'input[capture="environment"]',
    );
    await userEvent.upload(camera as HTMLInputElement, photo);
    await userEvent.type(nadia.getByLabelText("Année d'imposition"), "2025");
    await userEvent.type(nadia.getByLabelText("Revenu total (ligne 199)"), "18500");
    await userEvent.type(nadia.getByLabelText("Nom sur l'avis"), "Nadia Démo");
    await userEvent.type(nadia.getByLabelText("Code postal sur l'avis"), "h2x1y4");
    await userEvent.type(nadia.getByLabelText("Date de l'avis"), "2026-04-30");
    await userEvent.click(nadia.getByRole("checkbox", { name: /Avis vu en personne/ }));
    await userEvent.click(nadia.getByRole("button", { name: "Enregistrer l'avis" }));

    await waitFor(() => expect(within(summary()).getByText("Avis enregistré")).toBeVisible());
    const form = sentForm(fetchMock);
    expect(form.get("member")).toBe("m1");
    expect(form.get("did_not_file")).toBe("false");
    expect((form.get("file") as File).name).toBe("avis.jpg");
    expect(form.get("tax_year")).toBe("2025");
    expect(form.get("total_income_cents")).toBe("1850000");
    expect(form.get("postal_code_on_notice")).toBe("H2X 1Y4");
    expect(form.get("notice_date")).toBe("2026-04-30");
    expect(form.get("seen_in_person")).toBe("true");
    expect(await screen.findByText(/Le dossier est prêt pour la décision/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Remplacer cet avis" })).toBeVisible();
  });

  it("records 'did not file' with a reason and warns that the file goes to review", async () => {
    const fetchMock = mockApi(() =>
      Response.json(recorded({ did_not_file_reason: "Aucun revenu en 2025", has_file: false }), {
        status: 201,
      }),
    );
    await openPage();
    const nadia = within(card("Nadia Démo"));

    await userEvent.click(nadia.getByRole("checkbox", { name: /n'a pas produit de déclaration/ }));
    expect(nadia.queryByLabelText("Année d'imposition")).not.toBeInTheDocument();
    await userEvent.type(nadia.getByLabelText("Expliquez pourquoi"), "Aucun revenu en 2025");
    await userEvent.click(nadia.getByRole("button", { name: "Enregistrer l'avis" }));

    await waitFor(() => expect(within(summary()).getByText("N'a pas produit")).toBeVisible());
    const form = sentForm(fetchMock);
    expect(form.get("did_not_file")).toBe("true");
    expect(form.get("did_not_file_reason")).toBe("Aucun revenu en 2025");
    expect(form.has("file")).toBe(false);
    expect(await screen.findByText(/envoie le dossier en révision/)).toBeVisible();
  });

  it("shows the server's message on the field it refused", async () => {
    mockApi(() =>
      Response.json(
        {
          code: "validation_error",
          message: "Vérifiez les champs indiqués.",
          fields: { did_not_file_reason: ["Le motif est trop court."] },
        },
        { status: 400 },
      ),
    );
    await openPage();
    const nadia = within(card("Nadia Démo"));

    await userEvent.click(nadia.getByRole("checkbox", { name: /n'a pas produit de déclaration/ }));
    await userEvent.type(nadia.getByLabelText("Expliquez pourquoi"), "Non");
    await userEvent.click(nadia.getByRole("button", { name: "Enregistrer l'avis" }));

    expect(await nadia.findByText("Le motif est trop court.")).toBeVisible();
    expect(within(summary()).getByText("À enregistrer")).toBeVisible();
  });

  it("explains a refused save that has no field errors", async () => {
    mockApi(() =>
      Response.json(
        { code: "parse_error", message: "Malformed request.", fields: {} },
        { status: 400 },
      ),
    );
    await openPage();
    const nadia = within(card("Nadia Démo"));

    await userEvent.click(nadia.getByRole("checkbox", { name: /n'a pas produit de déclaration/ }));
    await userEvent.type(nadia.getByLabelText("Expliquez pourquoi"), "Aucun revenu en 2025");
    await userEvent.click(nadia.getByRole("button", { name: "Enregistrer l'avis" }));

    expect(
      await nadia.findByText("Le serveur a refusé d'enregistrer le dossier. Réessayez."),
    ).toBeVisible();
  });
  // rule: BR-DOC-007
  it("keeps Submit disabled until every adult has a notice or a reason", async () => {
    mockApi();
    await openPage();

    expect(screen.getByRole("button", { name: "Soumettre le dossier" })).toBeDisabled();
  });

  it("approves the file and says until when", async () => {
    const fetchMock = mockApi(() => Response.json(recorded(), { status: 201 }));
    await openPage();
    const nadia = within(card("Nadia Démo"));
    await userEvent.click(nadia.getByRole("checkbox", { name: /n'a pas produit de déclaration/ }));
    await userEvent.type(nadia.getByLabelText("Expliquez pourquoi"), "Aucun revenu en 2025");
    await userEvent.click(nadia.getByRole("button", { name: "Enregistrer l'avis" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Soumettre le dossier" })).toBeEnabled(),
    );
    await submitFile();

    await approve();

    expect(await screen.findByText(/Dossier approuvé jusqu'au 10 novembre 2027/)).toBeVisible();
    expect(
      fetchMock.mock.calls.some(
        ([input, init]) => String(input).endsWith(APPROVE_URL) && init?.method === "POST",
      ),
    ).toBe(true);
  });

  it("explains a file sent to review with each reason", async () => {
    mockApi(
      () =>
        Response.json(recorded({ did_not_file_reason: "Aucun revenu en 2025" }), { status: 201 }),
      () =>
        Response.json(
          decision({
            status: "review_required",
            status_reason: "DID_NOT_FILE, NAME_MISMATCH",
            approved_at: null,
            expires_at: null,
          }),
        ),
    );
    await openPage();
    await recordDidNotFile();
    await submitFile();

    await approve();

    expect(await screen.findByText("Dossier envoyé en révision")).toBeVisible();
    expect(screen.getByText("Un adulte n'a pas produit de déclaration de revenus.")).toBeVisible();
    expect(screen.getByText("Le nom sur un avis ne correspond pas à la personne.")).toBeVisible();
  });

  it("shows a rejection with its reason", async () => {
    mockApi(
      () =>
        Response.json(recorded({ did_not_file_reason: "Aucun revenu en 2025" }), { status: 201 }),
      () =>
        Response.json(
          decision({
            status: "rejected",
            status_reason: "INCOME_ABOVE_LICO",
            approved_at: null,
            expires_at: null,
          }),
        ),
    );
    await openPage();
    await recordDidNotFile();
    await submitFile();

    await approve();

    expect(await screen.findByText("Dossier refusé")).toBeVisible();
    expect(screen.getByText(/dépasse le seuil de faible revenu/)).toBeVisible();
  });

  it("shows why no decision was made when the file is incomplete", async () => {
    mockApi(
      () =>
        Response.json(recorded({ did_not_file_reason: "Aucun revenu en 2025" }), { status: 201 }),
      () =>
        Response.json(
          {
            code: "validation_error",
            message: "Vérifiez les champs indiqués.",
            fields: { non_field_errors: ["Complétez l'adresse et le téléphone du foyer."] },
          },
          { status: 400 },
        ),
    );
    await openPage();
    await recordDidNotFile();
    await submitFile();

    await approve();

    expect(await screen.findByText("Aucune décision n'a été prise")).toBeVisible();
    expect(screen.getByText("Complétez l'adresse et le téléphone du foyer.")).toBeVisible();
    expect(
      screen.getByRole("button", { name: /Approuver (le dossier|pour 12 mois)/ }),
    ).toBeVisible();
  });
});
