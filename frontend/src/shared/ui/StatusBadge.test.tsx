// AI contribution: 50% or more AI-generated
import { act, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { expectNoAxeViolations, renderWithProviders } from "../../test/render";
import i18n from "../i18n";
import en from "../i18n/en.json";
import fr from "../i18n/fr.json";
import { logger } from "../logger";
import { StatusBadge } from "./StatusBadge";
import { type StatusRecord, type StatusTone } from "./statusTones";

// The expected mapping is independent of statusTones, so an accidental tone change fails.
const cases: [StatusRecord, string, StatusTone][] = [
  ["household", "draft", "neutral"],
  ["household", "submitted", "info"],
  ["household", "awaiting_visit", "info"],
  ["household", "review_required", "warning"],
  ["household", "renewal_needed", "warning"],
  ["household", "approved", "success"],
  ["household", "suspended", "danger"],
  ["household", "rejected", "danger"],
  ["listing", "published", "success"],
  ["listing", "sold_out", "neutral"],
  ["listing", "closed", "neutral"],
  ["listing", "cancelled", "neutral"],
  ["reservation", "reserved", "info"],
  ["reservation", "picked_up", "success"],
  ["reservation", "cancelled", "neutral"],
  ["reservation", "cancelled_by_store", "warning"],
  ["reservation", "no_show", "danger"],
  ["partnerApplication", "submitted", "info"],
  ["partnerApplication", "approved", "success"],
  ["partnerApplication", "rejected", "danger"],
  ["store", "active", "success"],
  ["store", "deactivated", "neutral"],
  ["category", "active", "success"],
  ["category", "inactive", "neutral"],
];

const iconClasses = {
  info: "tabler-icon-info-circle",
  success: "tabler-icon-circle-check",
  warning: "tabler-icon-alert-triangle",
  danger: "tabler-icon-alert-circle",
};

describe("StatusBadge", () => {
  afterEach(() => vi.restoreAllMocks());

  it.each(cases)(
    "translates %s %s in both languages with the %s cue",
    async (record, status, tone) => {
      const { container } = renderWithProviders(<StatusBadge record={record} status={status} />);
      for (const [language, translations] of [
        ["fr", fr],
        ["en", en],
      ] as const) {
        await act(() => i18n.changeLanguage(language));
        const labels: Record<string, string> = translations.shared.status[record];
        const badge = container.querySelector("[data-tone]");
        expect(badge).toHaveAttribute("data-tone", tone);
        expect(badge).toHaveTextContent(labels[status]);
        expect(labels[status]).not.toBe(status);
      }
      const icon = container.querySelector("svg");
      if (tone === "neutral") expect(icon).toBeNull();
      else {
        expect(icon).toHaveAttribute("aria-hidden", "true");
        expect(icon).toHaveClass(iconClasses[tone]);
      }
      await expectNoAxeViolations(container);
    },
  );

  it.each(["future_status", "toString", "__proto__"])(
    "safely displays unknown %s and warns",
    (status) => {
      const warning = vi.spyOn(logger, "warning").mockImplementation(() => {});
      const { container } = renderWithProviders(<StatusBadge record="household" status={status} />);
      expect(screen.getByText(status).closest("[data-tone]")).toHaveAttribute(
        "data-tone",
        "neutral",
      );
      expect(container.querySelector("svg")).toBeNull();
      expect(warning).toHaveBeenCalledWith("unknown_status", { record: "household", status });
    },
  );
});
