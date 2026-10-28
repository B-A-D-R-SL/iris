// AI contribution: 50% or more AI-generated
import { Button } from "@mantine/core";
import { useForm } from "@mantine/form";
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { expectNoAxeViolations, renderWithProviders } from "../../test/render";
import i18n from "../i18n";
import {
  allOf,
  DateField,
  FileUpload,
  hasLength,
  isAcceptedFile,
  isMoneyInRange,
  isPhone,
  isPostalCode,
  isRequired,
  MoneyField,
  PhoneField,
  PostalCodeField,
  TextField,
} from "./index";

/** Keeps a field's value in state, like a form does, and reports every change. */
function Controlled<T>({
  initial,
  onValue,
  children,
}: {
  initial: T;
  onValue: (value: T) => void;
  children: (value: T, setValue: (value: T) => void) => React.ReactNode;
}) {
  const [value, setValue] = useState(initial);
  return children(value, (next) => {
    setValue(next);
    onValue(next);
  });
}

describe("TextField", () => {
  it("marks optional fields in the label and required ones for assistive technology", () => {
    renderWithProviders(
      <>
        <TextField label="Titre" value="" onChange={() => {}} />
        <TextField label="Description" optional value="" onChange={() => {}} />
      </>,
    );
    expect(screen.getByLabelText("Titre")).toHaveAttribute("aria-required", "true");
    expect(screen.getByLabelText("Description (facultatif)")).not.toHaveAttribute("aria-required");
  });

  it("returns the typed text and counts characters on long text", async () => {
    const onValue = vi.fn();
    renderWithProviders(
      <Controlled initial="" onValue={onValue}>
        {(value, setValue) => (
          <TextField
            label="Description"
            multiline
            maxLength={500}
            value={value}
            onChange={setValue}
          />
        )}
      </Controlled>,
    );
    await userEvent.type(screen.getByLabelText("Description"), "Pains d'hier");
    expect(onValue).toHaveBeenLastCalledWith("Pains d'hier");
    expect(screen.getByText("12 / 500")).toBeInTheDocument();
  });

  it("shows a server message with the same error style", () => {
    renderWithProviders(
      <TextField label="Titre" value="" onChange={() => {}} error="Titre déjà utilisé." />,
    );
    expect(screen.getByLabelText("Titre")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Titre déjà utilisé.")).toBeInTheDocument();
  });
});

describe("PostalCodeField", () => {
  it("stores the code in uppercase with one space", async () => {
    const onValue = vi.fn();
    renderWithProviders(
      <Controlled initial="" onValue={onValue}>
        {(value, setValue) => (
          <PostalCodeField label="Code postal" value={value} onChange={setValue} />
        )}
      </Controlled>,
    );
    const input = screen.getByLabelText("Code postal");
    await userEvent.type(input, "h2x1y4");
    expect(input).toHaveValue("H2X 1Y4");
    expect(onValue).toHaveBeenLastCalledWith("H2X 1Y4");
  });
});

describe("PhoneField", () => {
  it("shows (514) 555-0123 and stores E.164", async () => {
    const onValue = vi.fn();
    renderWithProviders(
      <Controlled initial="" onValue={onValue}>
        {(value, setValue) => <PhoneField label="Téléphone" value={value} onChange={setValue} />}
      </Controlled>,
    );
    const input = screen.getByLabelText("Téléphone");
    await userEvent.type(input, "5145550123");
    expect(input).toHaveValue("(514) 555-0123");
    expect(onValue).toHaveBeenLastCalledWith("+15145550123");
  });

  it("accepts a pasted number with the country code", async () => {
    const onValue = vi.fn();
    renderWithProviders(
      <Controlled initial="" onValue={onValue}>
        {(value, setValue) => <PhoneField label="Téléphone" value={value} onChange={setValue} />}
      </Controlled>,
    );
    await userEvent.click(screen.getByLabelText("Téléphone"));
    await userEvent.paste("+1 514 555 0123");
    expect(onValue).toHaveBeenLastCalledWith("+15145550123");
  });

  it("displays a stored number", () => {
    renderWithProviders(<PhoneField label="Téléphone" value="+15145550123" onChange={() => {}} />);
    expect(screen.getByLabelText("Téléphone")).toHaveValue("(514) 555-0123");
  });
});

describe("MoneyField", () => {
  it("takes dollars in French format and returns cents", async () => {
    const onValue = vi.fn();
    renderWithProviders(
      <Controlled<number | null> initial={null} onValue={onValue}>
        {(value, setValue) => (
          <MoneyField label="Valeur estimée" value={value} onChange={setValue} />
        )}
      </Controlled>,
    );
    const input = screen.getByLabelText("Valeur estimée");
    await userEvent.type(input, "12,5");
    expect(onValue).toHaveBeenLastCalledWith(1250);
    expect(input).toHaveAttribute("placeholder", "0,00 $");
  });

  it("uses $0.00 in English and returns null when cleared", async () => {
    await i18n.changeLanguage("en");
    const onValue = vi.fn();
    renderWithProviders(
      <Controlled<number | null> initial={2500} onValue={onValue}>
        {(value, setValue) => (
          <MoneyField label="Estimated value" value={value} onChange={setValue} />
        )}
      </Controlled>,
    );
    const input = screen.getByLabelText("Estimated value");
    expect(input).toHaveValue("$25.00");
    await userEvent.clear(input);
    expect(onValue).toHaveBeenLastCalledWith(null);
  });
});

describe("DateField", () => {
  it("returns the typed date as YYYY-MM-DD", async () => {
    const onValue = vi.fn();
    renderWithProviders(
      <Controlled<string | null> initial={null} onValue={onValue}>
        {(value, setValue) => (
          <DateField label="Meilleur avant" value={value} onChange={setValue} />
        )}
      </Controlled>,
    );
    const input = screen.getByLabelText("Meilleur avant");
    expect(input).toHaveAttribute("placeholder", "AAAA-MM-JJ");
    await userEvent.type(input, "2026-10-11");
    await waitFor(() => expect(onValue).toHaveBeenLastCalledWith("2026-10-11"));
  });
});

describe("FileUpload", () => {
  const photo = new File(["photo"], "pains.jpg", { type: "image/jpeg" });

  it("shows the limits, then the chosen file with change and remove", async () => {
    const onValue = vi.fn();
    const { container } = renderWithProviders(
      <Controlled<File | null> initial={null} onValue={onValue}>
        {(value, setValue) => (
          <FileUpload
            label="Photo"
            optional
            accept={["image/jpeg", "image/png"]}
            maxMb={5}
            buttonLabel="Prendre ou choisir une photo"
            value={value}
            onChange={setValue}
          />
        )}
      </Controlled>,
    );
    expect(screen.getByRole("button", { name: "Photo (facultatif)" })).toHaveTextContent(
      "JPG, PNG, 5 Mo maximum",
    );

    const input = container.querySelector<HTMLInputElement>('input[type="file"]');
    expect(input).toHaveAttribute("accept", "image/jpeg,image/png");
    await userEvent.upload(input!, photo);
    expect(onValue).toHaveBeenLastCalledWith(photo);
    expect(screen.getByText("pains.jpg")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Retirer" }));
    expect(onValue).toHaveBeenLastCalledWith(null);
    expect(screen.getByRole("button", { name: "Photo (facultatif)" })).toBeInTheDocument();
  });
});

/** A small form like the ones teammates will build, validated on submit. */
function ContactForm() {
  const form = useForm({
    initialValues: {
      name: "",
      postalCode: "",
      phone: "",
      value: null as number | null,
      bestBefore: null as string | null,
      photo: null as File | null,
    },
    validate: {
      name: allOf(isRequired(), hasLength({ min: 2, max: 80 })),
      postalCode: allOf(isRequired(), isPostalCode()),
      phone: allOf(isRequired(), isPhone()),
      value: isMoneyInRange({ maxCents: 100_000 }),
      photo: isAcceptedFile({ types: ["image/jpeg"], maxMb: 5 }),
    },
  });
  return (
    <form noValidate onSubmit={form.onSubmit(() => {})}>
      <TextField label="Titre" {...form.getInputProps("name")} />
      <PostalCodeField label="Code postal" {...form.getInputProps("postalCode")} />
      <PhoneField label="Téléphone" {...form.getInputProps("phone")} />
      <MoneyField label="Valeur estimée" optional {...form.getInputProps("value")} />
      <DateField label="Meilleur avant" optional {...form.getInputProps("bestBefore")} />
      <FileUpload
        label="Photo"
        optional
        accept={["image/jpeg"]}
        maxMb={5}
        {...form.getInputProps("photo")}
      />
      <Button type="submit">Publier</Button>
    </form>
  );
}

describe("shared fields in a @mantine/form form", () => {
  it("shows every error under its field, then follows the language switch", async () => {
    renderWithProviders(<ContactForm />);
    await userEvent.type(screen.getByLabelText("Code postal"), "h2x");
    await userEvent.click(screen.getByRole("button", { name: "Publier" }));

    expect(screen.getAllByText("Remplissez ce champ.")).toHaveLength(2);
    expect(screen.getByText(/Entrez un code postal canadien/)).toBeInTheDocument();
    expect(screen.getByLabelText("Téléphone")).toHaveAttribute("aria-invalid", "true");

    await act(() => i18n.changeLanguage("en"));
    expect(screen.getByText(/Enter a Canadian postal code/)).toBeInTheDocument();
  });

  it("has no accessibility violations, empty or with errors", async () => {
    const { container } = renderWithProviders(<ContactForm />);
    await expectNoAxeViolations(container);

    await userEvent.click(screen.getByRole("button", { name: "Publier" }));
    await expectNoAxeViolations(container);
  });
});
