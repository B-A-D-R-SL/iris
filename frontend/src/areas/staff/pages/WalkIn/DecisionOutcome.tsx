// AI contribution: 50% or more AI-generated
/** The decision on a walk-in file, in plain words: approved, rejected or in review (US-18). */
import { List } from "@mantine/core";
import { useTranslation } from "react-i18next";

import { formatDate } from "../../../../shared/forms";
import { Notice } from "../../../../shared/ui";
import type { ShownDecision } from "./shownDecision";
import { useLanguage } from "./useLanguage";

const REASON_KEYS: Record<string, string> = {
  INCOME_ABOVE_LICO: "staff.walkInNotices.reasonIncomeAboveLico",
  NOTICE_MISSING: "staff.walkInNotices.reasonNoticeMissing",
  NAME_MISMATCH: "staff.walkInNotices.reasonNameMismatch",
  ADDRESS_MISMATCH: "staff.walkInNotices.reasonAddressMismatch",
  NOTICE_NOT_SEEN: "staff.walkInNotices.reasonNoticeNotSeen",
  DID_NOT_FILE: "staff.walkInNotices.reasonDidNotFile",
  TAX_YEAR_NOT_ACCEPTED: "staff.walkInNotices.reasonTaxYear",
  INCOME_NOT_CONFIRMED: "staff.walkInNotices.reasonIncomeNotConfirmed",
  POSSIBLE_DUPLICATE: "staff.walkInNotices.reasonPossibleDuplicate",
};

/** Reason codes ("NAME_MISMATCH, NOTICE_NOT_SEEN") as translation keys; unknown codes stay as codes. */
function reasonKeys(statusReason: string): string[] {
  return statusReason
    .split(",")
    .map((code) => code.trim())
    .filter(Boolean)
    .map((code) => REASON_KEYS[code] ?? code);
}

function ApprovedUntil({ decision }: { decision: ShownDecision }) {
  const { t } = useTranslation();
  const language = useLanguage();
  const until = decision.expires_at ? formatDate(decision.expires_at, language) : "";
  return (
    <Notice type="success" title={t("staff.walkInNotices.approved", { date: until })}>
      {decision.invitation_not_sent
        ? t("staff.walkInNotices.invitationNotSent")
        : t("staff.walkInNotices.approvedHelp")}
    </Notice>
  );
}

/** Approved until a date, rejected with its reason, or sent to review with its reasons. */
export function DecisionOutcome({ decision }: { decision: ShownDecision }) {
  const { t } = useTranslation();
  if (decision.status === "approved") return <ApprovedUntil decision={decision} />;
  const rejected = decision.status === "rejected";
  return (
    <Notice
      type={rejected ? "error" : "warning"}
      title={t(rejected ? "staff.walkInNotices.rejected" : "staff.walkInNotices.sentToReview")}
    >
      <List size="sm">
        {reasonKeys(decision.status_reason).map((key) => (
          <List.Item key={key}>{t(key)}</List.Item>
        ))}
      </List>
    </Notice>
  );
}
