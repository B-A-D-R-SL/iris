// AI contribution: 50% or more AI-generated
import dayjs from "dayjs";
import { isValidElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";

import type { WalkInDraft } from "../../../../features/households/walkInApi";
import {
  DEFAULT_VALUES,
  MAX_OTHER_MEMBERS,
  emptyMember,
  fromDraft,
  relationKey,
  resumeStep,
  serverErrors,
  stepErrors,
  stepOf,
  stillToComplete,
  toPayload,
  type WalkInFormValues,
} from "./walkInForm";

const TODAY = dayjs("2026-11-02");

/** The translation key of a validation message, or null when the value passed. */
function messageKey(error: ReactNode): string | null {
  if (!error) return null;
  if (isValidElement<{ messageKey: string }>(error)) return error.props.messageKey;
  throw new Error("Not a validation message");
}

const holder: WalkInFormValues = {
  ...DEFAULT_VALUES,
  firstName: " Nadia ",
  lastName: "Démo",
  dateOfBirth: "1990-04-12",
  phone: "+15145550156",
  identityChecked: true,
  consentGiven: true,
};

const withAddress: WalkInFormValues = {
  ...holder,
  streetNumber: "1234A",
  streetName: "rue Saint-Denis",
  postalCode: "H2X 1Y4",
};

const child = {
  ...emptyMember(),
  firstName: "Léo",
  lastName: "Démo",
  dateOfBirth: "2017-01-03",
  relation: "child" as const,
};

describe("toPayload", () => {
  it("sends the holder trimmed, without an email as null, and no address before it is started", () => {
    expect(toPayload(holder)).toEqual({
      holder: {
        first_name: "Nadia",
        last_name: "Démo",
        date_of_birth: "1990-04-12",
        email: null,
        phone: "+15145550156",
        preferred_language: "fr",
      },
      identity_checked_in_person: true,
      consent_data_processing: true,
      members: [],
    });
  });

  it("sends a started address with the fixed province and an empty unit as null", () => {
    expect(toPayload(withAddress).address).toEqual({
      street_number: "1234A",
      street_name: "rue Saint-Denis",
      unit: null,
      city: "Montréal",
      province: "QC",
      postal_code: "H2X 1Y4",
    });
  });

  it("sends the other members with their relation, never the React key", () => {
    expect(toPayload({ ...holder, members: [child] }).members).toEqual([
      { first_name: "Léo", last_name: "Démo", date_of_birth: "2017-01-03", relation: "child" },
    ]);
  });
});

describe("fromDraft", () => {
  const draft = {
    id: "d1",
    email: null,
    phone: "+15145550156",
    preferred_language: "en",
    identity_checked_in_person: false,
    consent_data_processing_at: "2026-11-02T14:05:00Z",
    street_number: "",
    street_name: "",
    unit: "",
    city: "",
    postal_code: "",
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
        date_of_birth: "2017-01-03",
        relation: "child",
      },
    ],
  } as unknown as WalkInDraft;

  it("takes the holder from the member with relation holder and lists only the others", () => {
    const values = fromDraft(draft);
    expect(values).toMatchObject({
      firstName: "Nadia",
      dateOfBirth: "1990-04-12",
      email: "",
      preferredLanguage: "en",
      city: "Montréal",
      consentGiven: true,
    });
    expect(fromDraft({ ...draft, consent_data_processing_at: null }).consentGiven).toBe(false);
    expect(values.members).toEqual([
      {
        key: "m2",
        firstName: "Léo",
        lastName: "Démo",
        dateOfBirth: "2017-01-03",
        relation: "child",
      },
    ]);
  });
});

describe("stepErrors: holder", () => {
  it("requires the name, date of birth and phone", () => {
    const errors = stepErrors("holder", DEFAULT_VALUES, { today: TODAY });
    expect(Object.keys(errors).sort()).toEqual(
      ["consentGiven", "dateOfBirth", "firstName", "identityChecked", "lastName", "phone"].sort(),
    );
    expect(messageKey(errors.firstName)).toBe("shared.validation.required");
  });

  it.each([
    ["2008-11-02", null], // 18 today: accepted
    ["2008-11-03", "staff.walkIn.holderAge"], // 18 tomorrow
    ["1906-11-02", null], // exactly 120 years
    ["1906-11-01", "staff.walkIn.birthRange"],
    ["2026-11-03", "staff.walkIn.birthRange"], // future
    ["2026-02-31", "shared.validation.date"],
  ])("date of birth %s -> %s", (dateOfBirth, expected) => {
    const errors = stepErrors("holder", { ...holder, dateOfBirth }, { today: TODAY });
    expect(messageKey(errors.dateOfBirth)).toBe(expected);
  });

  it.each([
    ["Marie-Ève", null],
    ["O’Neil", null],
    ["Nadia2", "staff.walkIn.nameError"],
    ["--", "staff.walkIn.nameError"],
  ])("first name %s -> %s", (firstName, expected) => {
    const errors = stepErrors("holder", { ...holder, firstName }, { today: TODAY });
    expect(messageKey(errors.firstName)).toBe(expected);
  });

  it("checks an optional email only when it is typed", () => {
    expect(stepErrors("holder", { ...holder, email: "" }, { today: TODAY }).email).toBeUndefined();
    const errors = stepErrors("holder", { ...holder, email: "nadia@" }, { today: TODAY });
    expect(messageKey(errors.email)).toBe("shared.validation.email");
  });

  it("rejects an incomplete phone number", () => {
    const errors = stepErrors("holder", { ...holder, phone: "514555" }, { today: TODAY });
    expect(messageKey(errors.phone)).toBe("shared.validation.phone");
  });

  it("needs the photo ID check to move on, but not to save a draft", () => {
    const unchecked = { ...holder, identityChecked: false };
    expect(messageKey(stepErrors("holder", unchecked, { today: TODAY }).identityChecked)).toBe(
      "staff.walkIn.identityRequired",
    );
    expect(stepErrors("holder", unchecked, { today: TODAY, forDraft: true })).toEqual({});
  });

  it("needs the consent to move on, but not to save a draft", () => {
    const noConsent = { ...holder, consentGiven: false };
    expect(messageKey(stepErrors("holder", noConsent, { today: TODAY }).consentGiven)).toBe(
      "staff.walkIn.consentRequired",
    );
    expect(stepErrors("holder", noConsent, { today: TODAY, forDraft: true })).toEqual({});
  });
});

describe("stepErrors: address", () => {
  it("lets a draft be saved before the address is started", () => {
    expect(stepErrors("address", holder, { forDraft: true })).toEqual({});
    expect(Object.keys(stepErrors("address", holder))).toEqual(
      expect.arrayContaining(["streetNumber", "streetName", "postalCode"]),
    );
  });

  it.each([
    ["1234", null],
    ["1234A", null],
    ["12-3", null],
    ["A12", "staff.walkIn.streetNumberError"],
    ["12345678901", "staff.walkIn.streetNumberError"],
  ])("street number %s -> %s", (streetNumber, expected) => {
    expect(messageKey(stepErrors("address", { ...withAddress, streetNumber }).streetNumber)).toBe(
      expected,
    );
  });

  it("rejects a postal code that is not A1A 1A1 and a one-letter street", () => {
    const errors = stepErrors("address", { ...withAddress, postalCode: "H2X1Y", streetName: "a" });
    expect(messageKey(errors.postalCode)).toBe("shared.validation.postalCode");
    expect(messageKey(errors.streetName)).toBe("shared.validation.textLength");
  });
});

describe("stepErrors: members", () => {
  it("requires every field of each person, with paths per row", () => {
    const errors = stepErrors(
      "members",
      { ...holder, members: [child, emptyMember()] },
      { today: TODAY },
    );
    expect(Object.keys(errors).sort()).toEqual([
      "members.1.dateOfBirth",
      "members.1.firstName",
      "members.1.lastName",
      "members.1.relation",
    ]);
  });

  it("accepts a newborn but not a date in the future", () => {
    const born = (dateOfBirth: string) =>
      stepErrors("members", { ...holder, members: [{ ...child, dateOfBirth }] }, { today: TODAY });
    expect(born("2026-11-02")).toEqual({});
    expect(messageKey(born("2026-11-03")["members.0.dateOfBirth"])).toBe("staff.walkIn.birthRange");
  });

  it("allows 14 other people and refuses a 15th", () => {
    const people = (count: number) =>
      Array.from({ length: count }, () => ({ ...child, key: emptyMember().key }));
    expect(
      stepErrors("members", { ...holder, members: people(MAX_OTHER_MEMBERS) }, { today: TODAY }),
    ).toEqual({});
    const errors = stepErrors(
      "members",
      { ...holder, members: people(MAX_OTHER_MEMBERS + 1) },
      { today: TODAY },
    );
    expect(messageKey(errors.members)).toBe("staff.walkIn.tooManyPeople");
  });
});

describe("serverErrors", () => {
  it("puts each API field's message on the matching form field", () => {
    const { errors, other } = serverErrors({
      "holder.first_name": ["Prénom refusé."],
      "address.postal_code": ["Code postal refusé."],
      "members[1].relation": ["Lien refusé."],
      identity_checked_in_person: ["Refusé."],
      consent_data_processing: ["Consentement refusé."],
      non_field_errors: ["Fournissez au moins une modification."],
      holder: ["Entrez le téléphone."],
    });
    expect(errors).toEqual({
      firstName: "Prénom refusé.",
      postalCode: "Code postal refusé.",
      "members.1.relation": "Lien refusé.",
      identityChecked: "Refusé.",
      consentGiven: "Consentement refusé.",
    });
    expect(other).toEqual(["Fournissez au moins une modification.", "Entrez le téléphone."]);
  });
});

describe("navigation helpers", () => {
  it("finds the step of a field", () => {
    expect(stepOf("firstName")).toBe("holder");
    expect(stepOf("postalCode")).toBe("address");
    expect(stepOf("members.3.relation")).toBe("members");
  });

  it("resumes at the first step still missing information", () => {
    expect(resumeStep({ ...holder, identityChecked: false })).toBe("holder");
    expect(resumeStep({ ...holder, consentGiven: false })).toBe("holder");
    expect(resumeStep(holder)).toBe("address");
    expect(resumeStep(withAddress)).toBe("members");
  });

  it("lists what is still to complete; notices always remain for US-18", () => {
    expect(stillToComplete({ ...holder, identityChecked: false, consentGiven: false })).toEqual([
      "staff.walkIn.todoIdentity",
      "staff.walkIn.todoConsent",
      "staff.walkIn.todoAddress",
      "staff.walkIn.todoNotices",
    ]);
    expect(stillToComplete(withAddress)).toEqual(["staff.walkIn.todoNotices"]);
  });

  it("turns relations into translation keys", () => {
    expect(relationKey("spouse_partner")).toBe("spousePartner");
    expect(relationKey("other_relative")).toBe("otherRelative");
    expect(relationKey("child")).toBe("child");
  });
});
