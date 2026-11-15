// AI contribution: 50% or more AI-generated
/**
 * One adult's notice card (US-18, T-03.18.4): values, checks and the summary.
 * The checks follow BR-DOC-001 to BR-DOC-004 with the limits the API sends
 * (the notice_upload rule), so staff see mistakes at once; the server checks
 * them again and decides eligibility at approval.
 */
import type { ReactNode } from "react";

import type {
  DecisionSummary,
  NoticeInput,
  RecordedNotice,
} from "../../../../features/households/noticeApi";
import type { WalkInDraft } from "../../../../features/households/walkInApi";
import {
  hasLength,
  isAcceptedFile,
  isMoneyInRange,
  isPostalCode,
  isRequired,
  validationMessage,
} from "../../../../shared/forms";

export const NOTICE_TYPES = ["image/jpeg", "image/png", "application/pdf"] as const;

/** The notice_upload limits in force, from the decision summary. */
export type NoticeRules = DecisionSummary["notice_rules"];

/** The file limit in MB, as the upload field and its message show it. */
export const maxMb = (rules: NoticeRules) => rules.max_bytes / (1024 * 1024);

export type Member = WalkInDraft["members"][number];

export interface NoticeValues {
  didNotFile: boolean;
  reason: string;
  file: File | null;
  taxYear: number | string;
  totalIncomeCents: number | null;
  nameOnNotice: string;
  postalCodeOnNotice: string;
  noticeDate: string | null;
  seenInPerson: boolean;
}

export const EMPTY_NOTICE: NoticeValues = {
  didNotFile: false,
  reason: "",
  file: null,
  taxYear: "",
  totalIncomeCents: null,
  nameOnNotice: "",
  postalCodeOnNotice: "",
  noticeDate: null,
  seenInPerson: false,
};

/** Today in Montréal as "YYYY-MM-DD", whatever the device's time zone. */
export function montrealToday(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Montreal",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

/** BR-DOC-007: the members the API counts as adults, in the file's order. */
export function adultsOf(members: readonly Member[], adultIds: readonly string[]): Member[] {
  const wanted = new Set(adultIds);
  return members.filter((member) => wanted.has(member.id));
}

export const fullName = (member: Pick<Member, "first_name" | "last_name">) =>
  `${member.first_name} ${member.last_name}`.trim();

/** Field name -> message, empty when the card can be sent. */
export function noticeErrors(
  values: NoticeValues,
  today: string,
  rules: NoticeRules,
): Record<string, ReactNode> {
  const errors: Record<string, ReactNode> = {};
  const add = (field: keyof NoticeValues, message: ReactNode) => {
    if (message) errors[field] = message;
  };

  if (values.didNotFile) {
    const reason = values.reason.trim();
    add(
      "reason",
      reason ? hasLength({ min: 1, max: rules.reason_max_length })(reason) : isRequired()(""),
    );
    return errors;
  }

  add(
    "file",
    values.file
      ? isAcceptedFile({ types: NOTICE_TYPES, maxMb: maxMb(rules) })(values.file)
      : isRequired()(null),
  );

  const year = values.taxYear === "" ? null : Number(values.taxYear);
  add("taxYear", taxYearError(year, today, rules.earliest_tax_year));

  add(
    "totalIncomeCents",
    values.totalIncomeCents === null
      ? isRequired()(null)
      : isMoneyInRange({ maxCents: rules.max_income_cents })(values.totalIncomeCents),
  );
  add("nameOnNotice", isRequired()(values.nameOnNotice.trim()));
  add(
    "postalCodeOnNotice",
    values.postalCodeOnNotice.trim() ? isPostalCode()(values.postalCodeOnNotice) : isRequired()(""),
  );

  add("noticeDate", noticeDateError(values.noticeDate, today, year));
  return errors;
}

/** BR-DOC-002: a tax year from the rule's earliest year to last year. */
function taxYearError(year: number | null, today: string, earliest: number): ReactNode {
  if (year === null) return isRequired()("");
  const lastYear = Number(today.slice(0, 4)) - 1;
  if (Number.isInteger(year) && year >= earliest && year <= lastYear) return null;
  return validationMessage("staff.walkInNotices.taxYearRange", {
    min: earliest,
    max: lastYear,
  });
}

/** BR-DOC-002: after December 31 of the tax year and not after today. */
function noticeDateError(
  date: NoticeValues["noticeDate"],
  today: string,
  year: number | null,
): ReactNode {
  if (!date) return isRequired()(null);
  if (date > today) return validationMessage("shared.validation.dateMax", { date: today });
  if (year !== null && date <= `${year}-12-31`) {
    return validationMessage("staff.walkInNotices.dateAfterYear", { year });
  }
  return null;
}

/** The API input once the card has no errors. */
export function toNoticeInput(member: string, values: NoticeValues): NoticeInput {
  if (values.didNotFile) return { member, didNotFile: true, reason: values.reason.trim() };
  return {
    member,
    didNotFile: false,
    file: values.file as File,
    taxYear: Number(values.taxYear),
    totalIncomeCents: values.totalIncomeCents ?? 0,
    nameOnNotice: values.nameOnNotice.trim(),
    postalCodeOnNotice: values.postalCodeOnNotice.trim(),
    noticeDate: values.noticeDate ?? "",
    seenInPerson: values.seenInPerson,
  };
}

const SERVER_FIELDS: Record<string, keyof NoticeValues> = {
  did_not_file_reason: "reason",
  file: "file",
  tax_year: "taxYear",
  total_income_cents: "totalIncomeCents",
  name_on_notice: "nameOnNotice",
  postal_code_on_notice: "postalCodeOnNotice",
  notice_date: "noticeDate",
  seen_in_person: "seenInPerson",
};

/** Server field messages on the card's fields; the rest are shown above the card. */
export function noticeServerErrors(fields: Record<string, string[]>) {
  const errors: Record<string, string> = {};
  const other: string[] = [];
  for (const [field, messages] of Object.entries(fields)) {
    const key = SERVER_FIELDS[field];
    if (key) errors[key] = messages.join(" ");
    else other.push(...messages);
  }
  return { errors, other };
}

/** What the decision summary says about one adult. */
export type AdultState = "missing" | "filed" | "notSeen" | "didNotFile";

export function adultState(notice: RecordedNotice | undefined): AdultState {
  if (!notice) return "missing";
  if (notice.did_not_file_reason) return "didNotFile";
  return notice.seen_in_person ? "filed" : "notSeen";
}
