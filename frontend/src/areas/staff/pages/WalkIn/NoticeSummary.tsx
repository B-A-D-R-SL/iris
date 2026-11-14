// AI contribution: 50% or more AI-generated
/** What was recorded for one adult: a state badge and the saved values (US-18). */
import { Badge, List, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";

import type { RecordedNotice } from "../../../../features/households/noticeApi";
import { formatMoney } from "../../../../shared/forms";
import type { AdultState } from "./noticeForm";
import { useLanguage } from "./useLanguage";

const STATE_LABELS: Record<AdultState, string> = {
  missing: "staff.walkInNotices.stateMissing",
  filed: "staff.walkInNotices.stateFiled",
  notSeen: "staff.walkInNotices.stateNotSeen",
  didNotFile: "staff.walkInNotices.stateDidNotFile",
};

const STATE_COLORS: Record<AdultState, string> = {
  missing: "neutral",
  filed: "success",
  notSeen: "warning",
  didNotFile: "warning",
};

export function StateBadge({ state }: { state: AdultState }) {
  const { t } = useTranslation();
  return (
    <Badge color={STATE_COLORS[state]} variant="light">
      {t(STATE_LABELS[state])}
    </Badge>
  );
}

/** What was recorded, so staff can check it before the decision. */
export function RecordedSummary({ notice }: { notice: RecordedNotice }) {
  const { t } = useTranslation();
  const language = useLanguage();
  // The colon is part of the translation: French puts a space before it.
  const line = (label: string, value: string | number) =>
    t("staff.walkInNotices.line", { label: t(`staff.walkInNotices.${label}`), value });
  if (notice.did_not_file_reason) {
    return <Text size="sm">{line("reason", notice.did_not_file_reason)}</Text>;
  }
  const income =
    notice.total_income_cents == null
      ? t("staff.walkInNotices.notProvided")
      : formatMoney(notice.total_income_cents, language);
  return (
    <List size="sm" spacing={4}>
      <List.Item>
        {line("taxYear", notice.tax_year ?? t("staff.walkInNotices.notProvided"))}
      </List.Item>
      <List.Item>{line("totalIncome", income)}</List.Item>
      <List.Item>{line("nameOnNotice", notice.name_on_notice)}</List.Item>
      <List.Item>
        {line("noticeDate", notice.notice_date ?? t("staff.walkInNotices.notProvided"))}
      </List.Item>
    </List>
  );
}
