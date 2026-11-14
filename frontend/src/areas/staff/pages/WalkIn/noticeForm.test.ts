// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import type { RecordedNotice } from "../../../../features/households/noticeApi";
import { noticeFormData } from "../../../../features/households/noticeApi";
import {
  EMPTY_NOTICE,
  adultState,
  adults,
  ageOn,
  montrealToday,
  noticeErrors,
  noticeServerErrors,
  toNoticeInput,
  type Member,
  type NoticeValues,
} from "./noticeForm";

const TODAY = "2026-11-10";
const scan = () => new File(["%PDF-1.7"], "avis.pdf", { type: "application/pdf" });

const filed = (overrides: Partial<NoticeValues> = {}): NoticeValues => ({
  ...EMPTY_NOTICE,
  file: scan(),
  taxYear: 2025,
  totalIncomeCents: 1_850_000,
  nameOnNotice: "Nadia Démo",
  postalCodeOnNotice: "H2X 1Y4",
  noticeDate: "2026-04-30",
  seenInPerson: true,
  ...overrides,
});

const member = (id: string, dateOfBirth: string): Member =>
  ({
    id,
    first_name: "Prénom",
    last_name: id,
    date_of_birth: dateOfBirth,
    relation: "other",
  }) as Member;

const notice = (overrides: Partial<RecordedNotice> = {}): RecordedNotice =>
  ({
    id: "n1",
    member: "m1",
    status: "current",
    source: "walk_in",
    tax_year: 2025,
    total_income_cents: 1_850_000,
    name_on_notice: "Nadia Démo",
    postal_code_on_notice: "H2X 1Y4",
    notice_date: "2026-04-30",
    seen_in_person: true,
    did_not_file_reason: "",
    has_file: true,
    created_at: "2026-11-10T15:00:00Z",
    ...overrides,
  }) as RecordedNotice;

describe("dates and adults", () => {
  it("uses the Montréal date, not the device's", () => {
    // 03:30 UTC on Nov 11 is still Nov 10 in Montréal.
    expect(montrealToday(new Date("2026-11-11T03:30:00Z"))).toBe("2026-11-10");
  });

  it("counts whole years and keeps members 18 or older (BR-DOC-007)", () => {
    expect(ageOn("2008-11-10", TODAY)).toBe(18);
    expect(ageOn("2008-11-11", TODAY)).toBe(17);
    const people = [member("adult", "1990-04-12"), member("teen", "2010-01-01")];
    expect(adults(people, TODAY).map((person) => person.id)).toEqual(["adult"]);
  });
});

describe("noticeErrors", () => {
  it("accepts a complete filed notice", () => {
    expect(noticeErrors(filed(), TODAY)).toEqual({});
  });

  it("requires every value of a filed notice (BR-DOC-001)", () => {
    const errors = noticeErrors(EMPTY_NOTICE, TODAY);
    expect(Object.keys(errors).sort()).toEqual(
      [
        "file",
        "nameOnNotice",
        "noticeDate",
        "postalCodeOnNotice",
        "taxYear",
        "totalIncomeCents",
      ].sort(),
    );
  });

  it("checks the tax year, the date and the income range (BR-DOC-002)", () => {
    expect(noticeErrors(filed({ taxYear: 2026 }), TODAY)).toHaveProperty("taxYear");
    expect(noticeErrors(filed({ taxYear: 1999 }), TODAY)).toHaveProperty("taxYear");
    expect(noticeErrors(filed({ noticeDate: "2025-12-31" }), TODAY)).toHaveProperty("noticeDate");
    expect(noticeErrors(filed({ noticeDate: "2026-11-11" }), TODAY)).toHaveProperty("noticeDate");
    expect(noticeErrors(filed({ totalIncomeCents: 50_000_001 }), TODAY)).toHaveProperty(
      "totalIncomeCents",
    );
    expect(noticeErrors(filed({ totalIncomeCents: 0 }), TODAY)).toEqual({});
  });

  it("accepts only JPG, PNG or PDF up to 10 MB (BR-DOC-004)", () => {
    const text = new File(["x"], "avis.txt", { type: "text/plain" });
    expect(noticeErrors(filed({ file: text }), TODAY)).toHaveProperty("file");
  });

  it("asks only for a reason when the person did not file (BR-DOC-003)", () => {
    const none = { ...EMPTY_NOTICE, didNotFile: true };
    expect(Object.keys(noticeErrors(none, TODAY))).toEqual(["reason"]);
    expect(noticeErrors({ ...none, reason: "   " }, TODAY)).toHaveProperty("reason");
    expect(noticeErrors({ ...none, reason: "x".repeat(501) }, TODAY)).toHaveProperty("reason");
    expect(noticeErrors({ ...none, reason: "No income in 2025" }, TODAY)).toEqual({});
  });
});

describe("API body", () => {
  it("sends the API field names for a filed notice", () => {
    const data = noticeFormData(toNoticeInput("m1", filed()));
    expect(data.get("member")).toBe("m1");
    expect(data.get("did_not_file")).toBe("false");
    expect(data.get("tax_year")).toBe("2025");
    expect(data.get("total_income_cents")).toBe("1850000");
    expect(data.get("postal_code_on_notice")).toBe("H2X 1Y4");
    expect(data.get("notice_date")).toBe("2026-04-30");
    expect(data.get("seen_in_person")).toBe("true");
    expect((data.get("file") as File).name).toBe("avis.pdf");
  });

  it("sends only the trimmed reason when the person did not file", () => {
    const values = { ...EMPTY_NOTICE, didNotFile: true, reason: "  No income  ", file: scan() };
    const data = noticeFormData(toNoticeInput("m1", values));
    expect(data.get("did_not_file")).toBe("true");
    expect(data.get("did_not_file_reason")).toBe("No income");
    expect(data.has("file")).toBe(false);
    expect(data.has("tax_year")).toBe(false);
  });

  it("puts server messages on the card fields", () => {
    const { errors, other } = noticeServerErrors({
      tax_year: ["Enter an ended tax year."],
      member: ["Notices are recorded only for adults."],
    });
    expect(errors).toEqual({ taxYear: "Enter an ended tax year." });
    expect(other).toEqual(["Notices are recorded only for adults."]);
  });
});

describe("decision summary", () => {
  it("describes what each adult has recorded", () => {
    expect(adultState(undefined)).toBe("missing");
    expect(adultState(notice())).toBe("filed");
    expect(adultState(notice({ seen_in_person: false }))).toBe("notSeen");
    expect(adultState(notice({ did_not_file_reason: "No income" }))).toBe("didNotFile");
  });
});
