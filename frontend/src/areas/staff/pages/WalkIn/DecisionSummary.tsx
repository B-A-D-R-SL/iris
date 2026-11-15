// AI contribution: 50% or more AI-generated
/**
 * Decision summary (US-18, Figma W6.2b): each adult's state, household size, total
 * income and the low-income threshold, then Submit, then Approve behind a confirmation.
 * Every number and "ready" / "goes to review" answer comes from the API
 * (approval_views.py); the screen only shows them.
 */
import { Button, Group, List, Modal, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type {
  DecisionSummary as Summary,
  RecordedNotice,
} from "../../../../features/households/noticeApi";
import { formatDate, formatMoney } from "../../../../shared/forms";
import { Notice } from "../../../../shared/ui";
import { DecisionOutcome } from "./DecisionOutcome";
import { StateBadge } from "./NoticeSummary";
import { adultState, fullName, type Member } from "./noticeForm";
import { shownDecision } from "./shownDecision";
import { useDecision } from "./useDecision";
import { useLanguage } from "./useLanguage";
import classes from "./WalkIn.module.css";

function Fact({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text fw={600}>{value}</Text>
    </div>
  );
}

/** Household size, total income and the LICO threshold, as the API worked them out. */
function Facts({ summary }: { summary: Summary }) {
  const { t } = useTranslation();
  const language = useLanguage();
  const money = (cents: number | null) => (cents == null ? "—" : formatMoney(cents, language));
  return (
    <div className={classes.facts}>
      <Fact label={t("staff.walkInNotices.householdSize")} value={summary.household_size} />
      <Fact
        label={t("staff.walkInNotices.householdIncome")}
        value={money(summary.total_income_cents)}
      />
      <Fact label={t("staff.walkInNotices.threshold")} value={money(summary.threshold_cents)} />
    </div>
  );
}

/** Each adult and whether their notice is recorded. */
function AdultStates({
  adultMembers,
  notices,
}: Pick<DecisionSummaryProps, "adultMembers" | "notices">) {
  return (
    <List spacing="xs" mb="md">
      {adultMembers.map((member) => (
        <List.Item key={member.id}>
          <Group gap="xs">
            <Text size="sm">{fullName(member)}</Text>
            <StateBadge state={adultState(notices[member.id])} />
          </Group>
        </List.Item>
      ))}
    </List>
  );
}

interface ReadinessProps {
  /** Every adult has a notice or a non-filing reason. */
  complete: boolean;
  /** A saved notice is being replaced: the old values must not reach the decision. */
  replacing: boolean;
  review: boolean;
  /** The API's verdict on income against the threshold; null while it is not decided. */
  eligible: boolean | null;
}

function Readiness({ complete, replacing, review, eligible }: ReadinessProps) {
  const { t } = useTranslation();
  if (!complete) return <Text c="dimmed">{t("staff.walkInNotices.notReady")}</Text>;
  if (replacing) return <Text c="dimmed">{t("staff.walkInNotices.finishReplacing")}</Text>;
  if (review) return <Notice type="warning" title={t("staff.walkInNotices.review")} />;
  if (eligible === false) {
    return (
      <Notice type="error" title={t("staff.walkInNotices.notEligible")}>
        {t("staff.walkInNotices.notEligibleHelp")}
      </Notice>
    );
  }
  if (eligible) {
    return (
      <Notice type="success" title={t("staff.walkInNotices.eligible")}>
        {t("staff.walkInNotices.ready")}
      </Notice>
    );
  }
  return <Text>{t("staff.walkInNotices.ready")}</Text>;
}

interface ConfirmProps {
  /** Until when the file would be valid, as the API worked it out; null when unknown. */
  validUntil: string | null;
  opened: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

/** Approval is final and emails an invitation: ask first (Figma W6.3 S26). */
function ConfirmApproval({ validUntil, opened, onCancel, onConfirm }: ConfirmProps) {
  const { t } = useTranslation();
  const language = useLanguage();
  const until = validUntil ? formatDate(validUntil, language) : null;
  return (
    <Modal opened={opened} onClose={onCancel} title={t("staff.walkInNotices.confirmTitle")}>
      <Stack gap="md">
        {until && (
          <Text fw={600}>{t("staff.walkInNotices.confirmValidUntil", { date: until })}</Text>
        )}
        <Text>{t("staff.walkInNotices.confirmBody")}</Text>
        <Group justify="flex-end">
          <Button variant="subtle" onClick={onCancel}>
            {t("staff.walkInNotices.cancel")}
          </Button>
          <Button onClick={onConfirm}>{t("staff.walkInNotices.confirmApprove")}</Button>
        </Group>
      </Stack>
    </Modal>
  );
}

/** What went wrong with the last submit or approval request, if anything. */
function Problems({ submit, approve }: { submit: string | null; approve: string | null }) {
  const { t } = useTranslation();
  return (
    <>
      {submit && (
        <Notice type="error" title={t("staff.walkInNotices.notSubmitted")}>
          {submit}
        </Notice>
      )}
      {approve && (
        <Notice type="error" title={t("staff.walkInNotices.notDecided")}>
          {approve}
        </Notice>
      )}
    </>
  );
}

interface StepProps {
  status: string;
  ready: boolean;
  submitting: boolean;
  approving: boolean;
  /** Length of an approved file, from the file_validity rule; null when not known. */
  months: number | null;
  onSubmit: () => void;
  onApprove: () => void;
}

/** A draft is submitted first; a submitted file is approved. Other states have no action. */
function NextStep({
  status,
  ready,
  submitting,
  approving,
  months,
  onSubmit,
  onApprove,
}: StepProps) {
  const { t } = useTranslation();
  if (status !== "draft" && status !== "submitted") return null;
  const draft = status === "draft";
  return (
    <Stack gap={4} mt="md" align="flex-start">
      <Button
        onClick={draft ? onSubmit : onApprove}
        loading={draft ? submitting : approving}
        disabled={!ready}
      >
        {draft
          ? t("staff.walkInNotices.submit")
          : months
            ? t("staff.walkInNotices.approveFor", { count: months })
            : t("staff.walkInNotices.approve")}
      </Button>
      <Text size="sm" c="dimmed">
        {t(draft ? "staff.walkInNotices.submitHelp" : "staff.walkInNotices.approveHelp")}
      </Text>
    </Stack>
  );
}

interface DecisionSummaryProps {
  householdId: string;
  /** draft: submit first; submitted: approve; review_required, approved, rejected: decided. */
  status: string;
  statusReason: string;
  /** The saved expiry, so an approved file still shows its date after a reload. */
  expiresAt: string | null;
  replacing: boolean;
  adultMembers: Member[];
  notices: Record<string, RecordedNotice>;
}

/** Each adult's state, the numbers, the submit or approve button, then the decision. */
export function DecisionSummary(props: DecisionSummaryProps) {
  const { t } = useTranslation();
  const { summary, submission, approval, problem, submitProblem } = useDecision(props.householdId);
  const [confirming, setConfirming] = useState(false);
  const complete = Boolean(summary?.ready_for_decision);
  const ready = complete && !props.replacing;
  const decision = shownDecision(approval.data, props.status, props.statusReason, props.expiresAt);

  return (
    <section className={classes.card} aria-labelledby="decision-summary">
      <Title order={2} id="decision-summary" className={classes.memberTitle} mb="sm">
        {t("staff.walkInNotices.summaryTitle")}
      </Title>
      <AdultStates adultMembers={props.adultMembers} notices={props.notices} />
      {summary && <Facts summary={summary} />}
      {!decision && (
        <Readiness
          complete={complete}
          replacing={props.replacing}
          review={ready && Boolean(summary?.will_go_to_review)}
          eligible={summary?.eligible ?? null}
        />
      )}
      <Problems submit={submitProblem} approve={problem} />
      {decision ? (
        <DecisionOutcome decision={decision} />
      ) : (
        <NextStep
          status={props.status}
          ready={ready}
          submitting={submission.isPending}
          approving={approval.isPending}
          months={summary?.approved_months ?? null}
          onSubmit={() => submission.mutate()}
          onApprove={() => setConfirming(true)}
        />
      )}
      <ConfirmApproval
        validUntil={summary?.valid_until ?? null}
        opened={confirming}
        onCancel={() => setConfirming(false)}
        onConfirm={() => {
          setConfirming(false);
          approval.mutate();
        }}
      />
    </section>
  );
}
