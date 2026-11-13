// AI contribution: 50% or more AI-generated
/**
 * One adult's notice card (US-18, T-03.18.4): values, checks and the summary.
 * The checks mirror BR-DOC-001 to BR-DOC-004 so staff see mistakes at once;
 * the server checks them again and decides eligibility at approval.
 */
import type { ReactNode } from "react";

import type { NoticeInput, RecordedNotice } from "../../../../features/households/noticeApi";
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
export const NOTICE_MAX_MB = 10;
/** forms-and-fields.md: total income (line 199) is 0 to 500,000 $. */
export const MAX_INCOME_CENTS = 50_000_000;
export const MAX_REASON = 500;
export const FIRST_TAX_YEAR = 2000;

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

/** Age in whole years on a "YYYY-MM-DD" day. */
export function ageOn(dateOfBirth: string, day: string): number {
  const [by, bm, bd] = dateOfBirth.split("-").map(Number);
  const [y, m, d] = day.split("-").map(Number);
  return y - by - (m < bm || (m === bm && d < bd) ? 1 : 0);
}

/** BR-DOC-007: notices are recorded for members aged 18 or older. */
export function adults(members: readonly Member[], today: string): Member[] {
  return members.filter((member) => ageOn(member.date_of_birth, today) >= 18);
}

export const fullName = (member: Pick<Member, "first_name" | "last_name">) =>
  `${member.first_name} ${member.last_name}`.trim();

/** Field name -> message, empty when the card can be sent. */
export function noticeErrors(values: NoticeValues, today: string): Record<string, ReactNode> {
  const errors: Record<string, ReactNode> = {};
  const add = (field: keyof NoticeValues, message: ReactNode) => {
    if (message) errors[field] = message;
  };

  if (values.didNotFile) {
    const reason = values.reason.trim();
    add("reason", reason ? hasLength({ min: 1, max: MAX_REASON })(reason) : isRequired()(""));
    return errors;
  }

  add(
    "file",
    values.file
      ? isAcceptedFile({ types: NOTICE_TYPES, maxMb: NOTICE_MAX_MB })(values.file)
      : isRequired()(null),
  );

  const year = values.taxYear === "" ? null : Number(values.taxYear);
  add("taxYear", taxYearError(year, today));

  add(
    "totalIncomeCents",
    values.totalIncomeCents === null
      ? isRequired()(null)
      : isMoneyInRange({ maxCents: MAX_INCOME_CENTS })(values.totalIncomeCents),
  );
  add("nameOnNotice", isRequired()(values.nameOnNotice.trim()));
  add(
    "postalCodeOnNotice",
    values.postalCodeOnNotice.trim() ? isPostalCode()(values.postalCodeOnNotice) : isRequired()(""),
  );

  add("noticeDate", noticeDateError(values.noticeDate, today, year));
  return errors;
}

/** BR-DOC-002: a tax year from FIRST_TAX_YEAR to last year. */
function taxYearError(year: number | null, today: string): ReactNode {
  if (year === null) return isRequired()("");
  const lastYear = Number(today.slice(0, 4)) - 1;
  if (Number.isInteger(year) && year >= FIRST_TAX_YEAR && year <= lastYear) return null;
  return validationMessage("staff.walkInNotices.taxYearRange", {
    min: FIRST_TAX_YEAR,
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

/** Approval can be asked once every adult has a notice or a non-filing reason. */
export function readyForDecision(
  adultMembers: readonly Member[],
  notices: Readonly<Record<string, RecordedNotice>>,
): boolean {
  return adultMembers.length > 0 && adultMembers.every((member) => notices[member.id]);
}

/** Non-filing or an unseen notice sends the file to review (business-rules.md, #469). */
export function needsReview(notices: readonly RecordedNotice[]): boolean {
  return notices.some((notice) => adultState(notice) !== "filed");
}
