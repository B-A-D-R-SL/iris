// AI contribution: 50% or more AI-generated
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

export interface Filters {
  household: string;
  actor: string;
  from: string;
  to: string;
}
export const emptyFilters: Filters = { household: "", actor: "", from: "", to: "" };

export function useAuditLabels(): Record<string, string> {
  const { t } = useTranslation();
  return {
    admin: t("audit.search.roleAdmin"),
    intake_worker: t("audit.search.roleIntake"),
    store_staff: t("audit.search.roleStoreStaff"),
    store_manager: t("audit.search.roleStoreManager"),
    beneficiary: t("audit.search.roleBeneficiary"),
    view: t("audit.search.actionView"),
    decision: t("audit.search.actionDecision"),
    rule_published: t("audit.search.actionRulePublished"),
    suspend: t("audit.search.actionSuspend"),
    reactivate: t("audit.search.actionReactivate"),
    approved: t("audit.search.outcomeApproved"),
    rejected: t("audit.search.outcomeRejected"),
    review_required: t("audit.search.outcomeReview"),
    household: t("audit.search.targetHousehold"),
    rule_set_version: t("audit.search.targetRuleSetVersion"),
  };
}

export function useAuditFormatter(locale: string): Intl.DateTimeFormat {
  return useMemo(
    () =>
      new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "America/Montreal",
      }),
    [locale],
  );
}
