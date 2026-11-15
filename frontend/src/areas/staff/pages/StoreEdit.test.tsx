// AI contribution: 50% or more AI-generated
/** Editing, deactivating and reactivating a store (US-14, Figma W7.2 to W7.5). */
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";

import i18n from "../../../shared/i18n";
import { expectNoAxeViolations, renderWithProviders } from "../../../test/render";
import { demoStore, mockStoreApi, sentRequests } from "../../../test/staffStores";
import { StoreEdit } from "./StoreEdit";
import { Stores } from "./Stores";

const route = `/staff/stores/${demoStore.id}`;
const storePath = `/api/staff/stores/${demoStore.id}/`;

function renderEdit() {
  return renderWithProviders(
    <Routes>
      <Route path="/staff/stores" element={<Stores />} />
      <Route path="/staff/stores/:id" element={<StoreEdit />} />
    </Routes>,
    { route },
  );
}

async function loaded() {
  await screen.findByRole("heading", { name: demoStore.name, level: 1 });
}

const save = () =>
  userEvent.click(screen.getByRole("button", { name: "Enregistrer les modifications" }));

// Typing every opening hour with user-event is slow when the whole suite runs at once.
describe("StoreEdit", { timeout: 20_000 }, () => {
  it("shows every field, the summary and the status, without axe violations", async () => {
    mockStoreApi();
    const { container } = renderEdit();
    await loaded();

    expect(
      screen.getByText(/Partenaire depuis octobre 2026 · 3 offres en cours/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Nom du commerce/)).toHaveValue(demoStore.name);
    expect(screen.getByLabelText(/Code postal/)).toHaveValue("H2X 3K2");
    expect(screen.getByLabelText(/Téléphone/)).toHaveValue("(514) 555-0110");
    expect(screen.getByLabelText("Heure de fermeture, Jeu")).toHaveValue("21:00");
    expect(screen.getByLabelText("Dim fermé")).toBeChecked();
    expect(screen.getByRole("switch")).toBeChecked();
    await expectNoAxeViolations(container);
  });

  it("sends only the changed fields and returns to the list with a notice", async () => {
    const fetchMock = mockStoreApi();
    renderEdit();
    await loaded();

    const city = screen.getByLabelText(/Ville/);
    await userEvent.clear(city);
    await userEvent.type(city, "Laval");
    await save();

    expect(await screen.findByText("Modifications enregistrées")).toBeInTheDocument();
    expect(sentRequests(fetchMock, "PATCH")).toEqual([
      { path: storePath, body: { city: "Laval" } },
    ]);
  });

  it("checks fields and hours before sending anything", async () => {
    const fetchMock = mockStoreApi();
    renderEdit();
    await loaded();

    await userEvent.clear(screen.getByLabelText(/Code postal/));
    await userEvent.type(screen.getByLabelText(/Code postal/), "H2X 3K");
    const mondayClose = screen.getByLabelText("Heure de fermeture, Lun");
    await userEvent.clear(mondayClose);
    await userEvent.type(mondayClose, "07:00");
    await save();

    expect(await screen.findByText(/Corrigez 2 champs/)).toBeInTheDocument();
    expect(screen.getByText("Entrez un code postal comme H2X 1Y4.")).toBeInTheDocument();
    expect(
      screen.getByText("L’heure de fermeture doit suivre l’heure d’ouverture."),
    ).toBeInTheDocument();
    expect(sentRequests(fetchMock, "PATCH")).toEqual([]);
  });

  it("marks changed fields with * until they are saved or put back", async () => {
    mockStoreApi();
    renderEdit();
    await loaded();
    expect(screen.queryByText("Modifications non enregistrées")).toBeNull();

    const city = screen.getByLabelText(/^Ville/);
    await userEvent.clear(city);
    await userEvent.type(city, "Laval");
    expect(screen.getByLabelText("Ville *")).toBe(city);
    expect(screen.getByText("Modifications non enregistrées")).toBeInTheDocument();

    const mondayClose = screen.getByLabelText("Heure de fermeture, Lun");
    await userEvent.clear(mondayClose);
    await userEvent.type(mondayClose, "1900");
    expect(screen.getByText("Lun *")).toBeInTheDocument();
    expect(screen.getByText("Heures d’ouverture *")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("switch"));
    expect(screen.getByText("Statut *")).toBeInTheDocument();

    await userEvent.clear(city);
    await userEvent.type(city, "Montréal");
    await userEvent.clear(mondayClose);
    await userEvent.type(mondayClose, "2000");
    await userEvent.click(screen.getByRole("switch"));
    expect(screen.getByLabelText("Ville")).toBe(city);
    expect(screen.queryByText("Modifications non enregistrées")).toBeNull();
  });

  it("lets the admin type 24-hour times without a colon", async () => {
    mockStoreApi();
    renderEdit();
    await loaded();

    const mondayClose = screen.getByLabelText("Heure de fermeture, Lun");
    await userEvent.clear(mondayClose);
    await userEvent.type(mondayClose, "2000");
    expect(mondayClose).toHaveValue("20:00");

    const sundayOpen = screen.getByLabelText("Heure d’ouverture, Dim");
    await userEvent.click(screen.getByLabelText("Dim fermé"));
    await userEvent.type(sundayOpen, "8");
    await userEvent.tab();
    expect(sundayOpen).toHaveValue("08:00");
  });

  it("clears the hours error once every day is filled in", async () => {
    const empty = { mon: null, tue: null, wed: null, thu: null, fri: null, sat: null, sun: null };
    mockStoreApi({
      detail: () =>
        Response.json({ ...demoStore, opening_hours: { ...empty, notes: "Lun-ven 8 h-20 h" } }),
    });
    renderEdit();
    await loaded();

    await save();
    expect(await screen.findByText(/Corrigez 1 champs/)).toBeInTheDocument();

    for (const day of ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"]) {
      await userEvent.type(screen.getByLabelText(`Heure d’ouverture, ${day}`), "0800");
      await userEvent.type(screen.getByLabelText(`Heure de fermeture, ${day}`), "2000");
    }
    await userEvent.click(screen.getByLabelText("Dim fermé"));

    await waitFor(() => expect(screen.queryByText(/Corrigez/)).toBeNull());
    expect(screen.queryByText(/hours_invalid|invalid/)).toBeNull();
  });

  it("shows the server's field errors", async () => {
    mockStoreApi({
      patch: () =>
        Response.json(
          { code: "validation_error", message: "x", fields: { email: ["Courriel invalide."] } },
          { status: 400 },
        ),
    });
    renderEdit();
    await loaded();
    await userEvent.type(screen.getByLabelText(/Courriel/), "x");
    await save();
    expect(await screen.findByText("Courriel invalide.")).toBeInTheDocument();
  });

  it("deactivates with a required reason after showing what will be cancelled", async () => {
    const fetchMock = mockStoreApi();
    renderEdit();
    await loaded();

    await userEvent.click(screen.getByRole("switch"));
    await save();
    const dialog = await screen.findByRole("dialog", { name: "Désactiver ce commerce?" });
    expect(
      within(dialog).getByText("Ses 3 offres en cours sont annulées immédiatement."),
    ).toBeInTheDocument();
    expect(within(dialog).getByText(/Les 5 foyers qui avaient réservé/)).toBeInTheDocument();
    const confirm = within(dialog).getByRole("button", { name: "Désactiver le commerce" });
    expect(confirm).toBeDisabled();

    await userEvent.type(within(dialog).getByLabelText(/Motif/), "Fermé pour rénovations");
    await userEvent.click(confirm);

    expect(await screen.findByText("Commerce désactivé")).toBeInTheDocument();
    expect(sentRequests(fetchMock, "POST")).toEqual([
      { path: `${storePath}deactivate/`, body: { reason: "Fermé pour rénovations" } },
    ]);
    expect(sentRequests(fetchMock, "PATCH")).toEqual([]);
  });

  it("keeps the dialog open with the reason error from the server", async () => {
    mockStoreApi({
      deactivate: () =>
        Response.json(
          {
            code: "validation_error",
            message: "x",
            fields: { reason: ["Retirez les renseignements personnels."] },
          },
          { status: 400 },
        ),
    });
    renderEdit();
    await loaded();
    await userEvent.click(screen.getByRole("switch"));
    await save();
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText(/Motif/), "NAS 123 456 789");
    await userEvent.click(within(dialog).getByRole("button", { name: "Désactiver le commerce" }));
    expect(
      await within(dialog).findByText("Retirez les renseignements personnels."),
    ).toBeInTheDocument();
  });

  it("saves field changes first, then reactivates", async () => {
    const fetchMock = mockStoreApi({
      detail: () => Response.json({ ...demoStore, is_active: false }),
    });
    renderEdit();
    await loaded();
    expect(screen.getByText("Ce commerce est désactivé")).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText(/Ville/));
    await userEvent.type(screen.getByLabelText(/Ville/), "Laval");
    await userEvent.click(screen.getByRole("switch"));
    await save();
    const dialog = await screen.findByRole("dialog", { name: "Réactiver ce commerce?" });
    await userEvent.type(within(dialog).getByLabelText(/Motif/), "Rénovations terminées");
    await userEvent.click(within(dialog).getByRole("button", { name: "Réactiver le commerce" }));

    expect(await screen.findByText("Commerce réactivé")).toBeInTheDocument();
    const order = fetchMock.mock.calls
      .map(([, init]) => init?.method)
      .filter((method) => method === "PATCH" || method === "POST");
    expect(order).toEqual(["PATCH", "POST"]);
  });

  it("does not let the B.A.D.R. store be deactivated", async () => {
    mockStoreApi({ detail: () => Response.json({ ...demoStore, is_badr: true }) });
    renderEdit();
    await loaded();
    expect(screen.getByRole("switch")).toBeDisabled();
    expect(
      screen.getByText("Le commerce B.A.D.R. ne peut pas être désactivé."),
    ).toBeInTheDocument();
  });

  it("says when the store does not exist", async () => {
    mockStoreApi({
      detail: () => Response.json({ code: "not_found", message: "x", fields: {} }, { status: 404 }),
    });
    renderEdit();
    expect(await screen.findByText("Ce commerce n’existe pas.")).toBeInTheDocument();
  });

  it("shows a notice when the connection fails while saving", async () => {
    mockStoreApi({ patch: () => Promise.reject(new TypeError("offline")) as never });
    renderEdit();
    await loaded();
    await userEvent.type(screen.getByLabelText(/Ville/), "x");
    await save();
    expect(
      await screen.findByText("Les modifications n’ont pas été enregistrées"),
    ).toBeInTheDocument();
  });

  it("is in English when the language is switched", async () => {
    mockStoreApi();
    renderEdit();
    await loaded();
    await act(() => i18n.changeLanguage("en"));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Save changes" })).toBeInTheDocument(),
    );
    expect(screen.getByText("Opening hours")).toBeInTheDocument();
    await act(() => i18n.changeLanguage("fr"));
  });
});
