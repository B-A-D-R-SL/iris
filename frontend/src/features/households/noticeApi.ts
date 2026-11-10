// AI contribution: 50% or more AI-generated
/**
 * Walk-in notices of assessment (US-18, T-03.18.2 endpoint): one multipart POST
 * per adult records the scan and typed values, or a non-filing reason. The
 * server checks the staff role and BR-DOC-001 to BR-DOC-007 again.
 */
import { csrfToken } from "../../shared/api/csrf";
import type { components } from "../../shared/api/generated";
import { WalkInFailed } from "./walkInApi";

export type RecordedNotice = components["schemas"]["WalkInNoticeRead"];

/** What staff send for one adult; empty values are left out of the form data. */
export type NoticeInput =
  | {
      member: string;
      didNotFile: false;
      file: File;
      taxYear: number;
      totalIncomeCents: number;
      nameOnNotice: string;
      postalCodeOnNotice: string;
      noticeDate: string;
      seenInPerson: boolean;
    }
  | { member: string; didNotFile: true; reason: string };

/** The multipart body with the API's field names. */
export function noticeFormData(input: NoticeInput): FormData {
  const data = new FormData();
  data.append("member", input.member);
  if (input.didNotFile) {
    data.append("did_not_file", "true");
    data.append("did_not_file_reason", input.reason);
    return data;
  }
  data.append("did_not_file", "false");
  data.append("file", input.file, input.file.name);
  data.append("tax_year", String(input.taxYear));
  data.append("total_income_cents", String(input.totalIncomeCents));
  data.append("name_on_notice", input.nameOnNotice);
  data.append("postal_code_on_notice", input.postalCodeOnNotice);
  data.append("notice_date", input.noticeDate);
  data.append("seen_in_person", input.seenInPerson ? "true" : "false");
  return data;
}

function errorBody(value: unknown): { message: string; fields: Record<string, string[]> } | null {
  if (typeof value !== "object" || value === null) return null;
  const { message, fields } = value as Record<string, unknown>;
  if (typeof message !== "string") return null;
  return { message, fields: typeof fields === "object" && fields ? (fields as never) : {} };
}

export const noticesQueryKey = (householdId: string) =>
  ["walk-in", householdId, "notices"] as const;

/** The current notice of each member, so staff can resume a file after a reload. */
export async function listNotices(
  householdId: string,
  language: "fr" | "en",
): Promise<RecordedNotice[]> {
  const response = await fetch(`/api/staff/households/${householdId}/notices/`, {
    method: "GET",
    headers: { Accept: "application/json", "Accept-Language": language },
    credentials: "same-origin",
  });
  if (response.ok) return (await response.json()) as RecordedNotice[];

  const body = errorBody(await response.json().catch(() => null));
  throw new WalkInFailed(response.status, body?.message ?? "", body?.fields ?? {});
}

/** Records one adult's notice; refused requests throw WalkInFailed (400 has field messages). */
export async function recordNotice(
  householdId: string,
  input: NoticeInput,
  language: "fr" | "en",
): Promise<RecordedNotice> {
  // No Content-Type: the browser sets the multipart boundary itself.
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Accept-Language": language,
  };
  const token = csrfToken();
  if (token) headers["X-CSRFToken"] = token;
  const response = await fetch(`/api/staff/households/${householdId}/notices/`, {
    method: "POST",
    headers,
    body: noticeFormData(input),
    credentials: "same-origin",
  });
  if (response.ok) return (await response.json()) as RecordedNotice;

  const body = errorBody(await response.json().catch(() => null));
  throw new WalkInFailed(response.status, body?.message ?? "", body?.fields ?? {});
}

export type WalkInDecision = components["schemas"]["WalkInDecision"];

/** Asks for the decision (approved, rejected or review_required); 400 means the file is incomplete. */
export async function approveWalkIn(
  householdId: string,
  language: "fr" | "en",
): Promise<WalkInDecision> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Accept-Language": language,
  };
  const token = csrfToken();
  if (token) headers["X-CSRFToken"] = token;
  const response = await fetch(`/api/staff/households/${householdId}/approve/`, {
    method: "POST",
    headers,
    credentials: "same-origin",
  });
  if (response.ok) return (await response.json()) as WalkInDecision;

  const body = errorBody(await response.json().catch(() => null));
  throw new WalkInFailed(response.status, body?.message ?? "", body?.fields ?? {});
}
