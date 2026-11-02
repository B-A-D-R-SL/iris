// AI contribution: 50% or more AI-generated
/**
 * Values, checks and API mapping of the walk-in form (forms-and-fields.md,
 * "Walk-in registration": registration steps 1 to 3 plus the photo ID check).
 * The server checks everything again; its 400 messages appear on the matching fields.
 */
import dayjs, { type Dayjs } from "dayjs";
import type { ReactNode } from "react";

import type {
  MemberRelation,
  WalkInDraft,
  WalkInInput,
} from "../../../../features/households/walkInApi";
import {
  allOf,
  hasLength,
  isDateInRange,
  isEmail,
  isPhone,
  isPostalCode,
  isRequired,
  validationMessage,
  type Rule,
} from "../../../../shared/forms";

export const STEPS = ["holder", "address", "members", "review"] as const;
export type Step = (typeof STEPS)[number];

/** 15 people at most, the holder included (forms-and-fields.md, step 3). */
export const MAX_OTHER_MEMBERS = 14;

export const RELATIONS: readonly MemberRelation[] = [
  "spouse_partner",
  "child",
  "parent",
  "sibling",
  "grandparent",
  "grandchild",
  "other_relative",
  "other",
];

/** "spouse_partner" -> the translation key's last part, "spousePartner". */
export const relationKey = (relation: MemberRelation) =>
  relation.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());

export interface MemberValues {
  /** Only for React lists; never sent. */
  key: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string | null;
  relation: MemberRelation | "";
}

export interface WalkInFormValues {
  firstName: string;
  lastName: string;
  dateOfBirth: string | null;
  email: string;
  /** E.164 from PhoneField, for example "+15145550123". */
  phone: string;
  preferredLanguage: "fr" | "en";
  identityChecked: boolean;
  streetNumber: string;
  streetName: string;
  unit: string;
  city: string;
  postalCode: string;
  members: MemberValues[];
}

export const DEFAULT_VALUES: WalkInFormValues = {
  firstName: "",
  lastName: "",
  dateOfBirth: null,
  email: "",
  phone: "",
  preferredLanguage: "fr",
  identityChecked: false,
  streetNumber: "",
  streetName: "",
  unit: "",
  city: "Montréal",
  postalCode: "",
  members: [],
};

let nextKey = 0;
export function emptyMember(): MemberValues {
  nextKey += 1;
  return { key: `member-${nextKey}`, firstName: "", lastName: "", dateOfBirth: null, relation: "" };
}

/** The form values of a saved draft. The holder is the member with relation "holder". */
export function fromDraft(draft: WalkInDraft): WalkInFormValues {
  const holder = draft.members.find((member) => member.relation === "holder");
  return {
    firstName: holder?.first_name ?? "",
    lastName: holder?.last_name ?? "",
    dateOfBirth: holder?.date_of_birth ?? null,
    email: draft.email ?? "",
    phone: draft.phone,
    preferredLanguage: draft.preferred_language,
    identityChecked: draft.identity_checked_in_person,
    streetNumber: draft.street_number,
    streetName: draft.street_name,
    unit: draft.unit ?? "",
    city: draft.city || DEFAULT_VALUES.city,
    postalCode: draft.postal_code,
    members: draft.members
      .filter((member) => member.relation !== "holder")
      .map((member) => ({
        key: member.id,
        firstName: member.first_name,
        lastName: member.last_name,
        dateOfBirth: member.date_of_birth,
        relation: member.relation as MemberRelation,
      })),
  };
}

/** True once any part of the address was typed (the city has a default). */
export function hasAddress(values: WalkInFormValues): boolean {
  return [values.streetNumber, values.streetName, values.unit, values.postalCode].some(
    (value) => value.trim() !== "",
  );
}

/** The request body for POST or PATCH, from values that passed stepErrors. */
export function toPayload(values: WalkInFormValues): WalkInInput {
  const body: WalkInInput = {
    holder: {
      first_name: values.firstName.trim(),
      last_name: values.lastName.trim(),
      date_of_birth: values.dateOfBirth ?? "",
      email: values.email.trim() || null,
      phone: values.phone,
      preferred_language: values.preferredLanguage,
    },
    identity_checked_in_person: values.identityChecked,
    members: values.members.map((member) => ({
      first_name: member.firstName.trim(),
      last_name: member.lastName.trim(),
      date_of_birth: member.dateOfBirth ?? "",
      relation: member.relation as MemberRelation,
    })),
  };
  if (hasAddress(values)) {
    body.address = {
      street_number: values.streetNumber.trim(),
      street_name: values.streetName.trim(),
      unit: values.unit.trim() || null,
      city: values.city.trim(),
      province: "QC",
      postal_code: values.postalCode,
    };
  }
  return body;
}

// ---------------------------------------------------------------- checks

const NAME = /^[\p{L} '’-]+$/u;
const STREET_NUMBER = /^\d{1,8}[a-zA-Z]?(?:[/-]\d{1,3})?$/;
const DATE = "YYYY-MM-DD";

const required = isRequired();

function isName(): Rule<string> {
  return (value) =>
    value.trim() === "" || (NAME.test(value.trim()) && /\p{L}/u.test(value))
      ? null
      : validationMessage("staff.walkIn.nameError");
}

const name = allOf<string>(required, hasLength({ max: 100 }), isName());

/** Born within the last 120 years; the holder is also 18 or older. */
function birthDate(today: Dayjs, holder: boolean): Rule<string | null> {
  const oldest = today.subtract(120, "year").format(DATE);
  const youngest = today.format(DATE);
  const adult = today.subtract(18, "year").format(DATE);
  return allOf<string | null>(required, isDateInRange(), (value) => {
    if (!value) return null;
    if (value < oldest || value > youngest) return validationMessage("staff.walkIn.birthRange");
    if (holder && value > adult) return validationMessage("staff.walkIn.holderAge");
    return null;
  });
}

type Errors = Record<string, ReactNode>;

function collect(errors: Errors, field: string, error: ReactNode) {
  if (error) errors[field] = error;
}

function holderErrors(values: WalkInFormValues, today: Dayjs, forDraft: boolean): Errors {
  const errors: Errors = {};
  collect(errors, "firstName", name(values.firstName));
  collect(errors, "lastName", name(values.lastName));
  collect(errors, "dateOfBirth", birthDate(today, true)(values.dateOfBirth));
  collect(errors, "email", isEmail()(values.email));
  collect(errors, "phone", allOf<string>(required, isPhone())(values.phone));
  // A draft may be saved before the ID is seen; moving on needs it (required field).
  if (!forDraft && !values.identityChecked) {
    errors.identityChecked = validationMessage("staff.walkIn.identityRequired");
  }
  return errors;
}

function addressErrors(values: WalkInFormValues): Errors {
  const errors: Errors = {};
  collect(
    errors,
    "streetNumber",
    allOf<string>(required, (value) =>
      STREET_NUMBER.test(value.trim()) ? null : validationMessage("staff.walkIn.streetNumberError"),
    )(values.streetNumber),
  );
  collect(
    errors,
    "streetName",
    allOf<string>(required, hasLength({ min: 2, max: 120 }))(values.streetName),
  );
  collect(errors, "unit", hasLength({ max: 10 })(values.unit));
  collect(errors, "city", allOf<string>(required, hasLength({ max: 80 }))(values.city));
  collect(errors, "postalCode", allOf<string>(required, isPostalCode())(values.postalCode));
  return errors;
}

function memberErrors(values: WalkInFormValues, today: Dayjs): Errors {
  const errors: Errors = {};
  values.members.forEach((member, index) => {
    const at = `members.${index}`;
    collect(errors, `${at}.firstName`, name(member.firstName));
    collect(errors, `${at}.lastName`, name(member.lastName));
    collect(errors, `${at}.dateOfBirth`, birthDate(today, false)(member.dateOfBirth));
    collect(errors, `${at}.relation`, required(member.relation));
  });
  if (values.members.length > MAX_OTHER_MEMBERS) {
    errors.members = validationMessage("staff.walkIn.tooManyPeople");
  }
  return errors;
}

/**
 * Errors of one step. `forDraft` relaxes only what may wait in a draft:
 * the photo ID check, and an address that has not been started yet.
 */
export function stepErrors(
  step: Step,
  values: WalkInFormValues,
  { today = dayjs(), forDraft = false }: { today?: Dayjs; forDraft?: boolean } = {},
): Errors {
  switch (step) {
    case "holder":
      return holderErrors(values, today, forDraft);
    case "address":
      return forDraft && !hasAddress(values) ? {} : addressErrors(values);
    case "members":
      return memberErrors(values, today);
    case "review":
      return {
        ...holderErrors(values, today, forDraft),
        ...(forDraft && !hasAddress(values) ? {} : addressErrors(values)),
        ...memberErrors(values, today),
      };
  }
}

/** The step that shows a form field, for jumping to the first error. */
export function stepOf(field: string): Step {
  if (field.startsWith("members")) return "members";
  if (["streetNumber", "streetName", "unit", "city", "postalCode"].includes(field))
    return "address";
  return "holder";
}

/** Where to resume a saved draft: the first step still missing information. */
export function resumeStep(values: WalkInFormValues): Step {
  if (!values.identityChecked) return "holder";
  if (!hasAddress(values)) return "address";
  return "members";
}

/** What is still missing before notices and approval (US-18), as translation keys. */
export function stillToComplete(values: WalkInFormValues): string[] {
  const todo: string[] = [];
  if (!values.identityChecked) todo.push("staff.walkIn.todoIdentity");
  if (!hasAddress(values)) todo.push("staff.walkIn.todoAddress");
  todo.push("staff.walkIn.todoNotices");
  return todo;
}

// ---------------------------------------------------------------- server errors

const HOLDER_FIELDS: Record<string, keyof WalkInFormValues> = {
  first_name: "firstName",
  last_name: "lastName",
  date_of_birth: "dateOfBirth",
  email: "email",
  phone: "phone",
  preferred_language: "preferredLanguage",
};
const ADDRESS_FIELDS: Record<string, keyof WalkInFormValues> = {
  street_number: "streetNumber",
  street_name: "streetName",
  unit: "unit",
  city: "city",
  postal_code: "postalCode",
};
const MEMBER_FIELDS: Record<string, keyof MemberValues> = {
  first_name: "firstName",
  last_name: "lastName",
  date_of_birth: "dateOfBirth",
  relation: "relation",
};

/** "holder.first_name" -> "firstName"; "members[1].relation" -> "members.1.relation". */
function formField(apiField: string): string | null {
  const [group, rest] = apiField.split(/\.(.*)/s);
  if (group === "holder" && rest && HOLDER_FIELDS[rest]) return HOLDER_FIELDS[rest];
  if (group === "address" && rest && ADDRESS_FIELDS[rest]) return ADDRESS_FIELDS[rest];
  if (apiField === "identity_checked_in_person") return "identityChecked";
  const member = /^members\[(\d+)\]\.(\w+)$/.exec(apiField);
  if (member && MEMBER_FIELDS[member[2]]) return `members.${member[1]}.${MEMBER_FIELDS[member[2]]}`;
  return null;
}

/** Splits a 400 response into field errors and the messages no field can show. */
export function serverErrors(fields: Record<string, string[]>) {
  const errors: Record<string, string> = {};
  const other: string[] = [];
  for (const [apiField, messages] of Object.entries(fields)) {
    const field = formField(apiField);
    if (field) errors[field] = messages.join(" ");
    else other.push(...messages);
  }
  return { errors, other };
}
