// AI contribution: 50% or more AI-generated
/**
 * Walk-in notices and decision summary (US-18, T-03.18.4).
 * One card per adult: photograph the notice with the device camera (or choose
 * a file), type the tax year and line-199 income, or record "did not file"
 * with a reason. The summary below shows what each adult has.
 *
 * Notices are recorded on the draft (BR-DOC-007). Once every adult has one,
 * "Submit the file" runs the US-25 duplicate check; then
 * "Approve the file" asks the server for the decision (approve_walk_in, #469):
 * eligibility decides between approved, rejected and review (BR-DUP-002).
 * Saved notices are loaded on open, and approval waits while a saved notice is
 * being replaced.
 */
import {
  Badge,
  Button,
  Checkbox,
  FileButton,
  Group,
  List,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useIsMutating, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { IconCamera, IconCircleCheck } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import {
  approveWalkIn,
  submitWalkIn,
  listNotices,
  noticesQueryKey,
  recordNotice,
  type RecordedNotice,
  type WalkInDecision,
} from "../../../../features/households/noticeApi";
import {
  WalkInFailed,
  getWalkIn,
  walkInQueryKey,
  type WalkInDraft,
} from "../../../../features/households/walkInApi";
import {
  DateField,
  FileUpload,
  IntegerField,
  MoneyField,
  PostalCodeField,
  TextField,
  formatMoney,
} from "../../../../shared/forms";
import { ErrorState, LoadingState, Notice } from "../../../../shared/ui";
import classes from "./WalkIn.module.css";
import {
  EMPTY_NOTICE,
  FIRST_TAX_YEAR,
  MAX_REASON,
  NOTICE_MAX_MB,
  NOTICE_TYPES,
  adultState,
  adults,
  fullName,
  montrealToday,
  needsReview,
  noticeErrors,
  noticeServerErrors,
  readyForDecision,
  toNoticeInput,
  type AdultState,
  type Member,
  type NoticeValues,
} from "./noticeForm";

const useLanguage = () => {
  const { i18n } = useTranslation();
  return i18n.resolvedLanguage === "en" ? "en" : "fr";
};

/** /staff/walk-in/:id/notices */
export function Notices() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const language = useLanguage();
  const query = useQuery({
    queryKey: walkInQueryKey(id),
    queryFn: () => getWalkIn(id, language),
    staleTime: Infinity,
  });
  // Notices already saved, so a reload or a return from the file keeps them.
  const saved = useQuery({
    queryKey: noticesQueryKey(id),
    queryFn: () => listNotices(id, language),
  });

  if (query.isPending || saved.isPending) return <LoadingState />;
  if (query.isError) {
    if (query.error instanceof WalkInFailed && query.error.status === 404) {
      return <Notice type="error" title={t("staff.walkIn.notFound")} />;
    }
    return <ErrorState onRetry={() => void query.refetch()} />;
  }
  if (saved.isError) return <ErrorState onRetry={() => void saved.refetch()} />;
  return <NoticesPage draft={query.data} saved={saved.data} />;
}

const approveMutationKey = (householdId: string) => ["walk-in", householdId, "approve"] as const;
const submitMutationKey = (householdId: string) => ["walk-in", householdId, "submit"] as const;

function NoticesPage({ draft, saved }: { draft: WalkInDraft; saved: RecordedNotice[] }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [today] = useState(montrealToday);
  const adultMembers = adults(draft.members, today);
  const notices: Record<string, RecordedNotice> = Object.fromEntries(
    saved.map((notice) => [notice.member, notice]),
  );
  // Adults whose saved notice is being replaced: approval waits until each is saved or cancelled.
  const [replacing, setReplacing] = useState<ReadonlySet<string>>(new Set());
  const deciding =
    useIsMutating({ mutationKey: approveMutationKey(draft.id) }) +
      useIsMutating({ mutationKey: submitMutationKey(draft.id) }) >
    0;
  const open = draft.status === "draft";
  const holder = draft.members.find((member) => member.relation === "holder");

  const setMemberReplacing = (memberId: string, on: boolean) =>
    setReplacing((current) => {
      const next = new Set(current);
      if (on) next.add(memberId);
      else next.delete(memberId);
      return next;
    });

  const keepNotice = (notice: RecordedNotice) =>
    queryClient.setQueryData<RecordedNotice[]>(noticesQueryKey(draft.id), (list = []) => [
      ...list.filter((entry) => entry.member !== notice.member),
      notice,
    ]);

  return (
    <Stack gap="lg">
      <div>
        <Text className={classes.eyebrow}>{t("staff.walkIn.eyebrow")}</Text>
        <Title order={1}>{t("staff.walkInNotices.title")}</Title>
        <Text c="gray.7">
          {t("staff.walkInNotices.description", { name: holder ? fullName(holder) : "" })}
        </Text>
      </div>

      {!open && <Notice type="info" title={t("staff.walkInNotices.notDraft")} />}
      {adultMembers.length === 0 && (
        <Notice type="error" title={t("staff.walkInNotices.noAdults")} />
      )}

      {adultMembers.map((member) => (
        <NoticeCard
          key={member.id}
          householdId={draft.id}
          member={member}
          today={today}
          recorded={notices[member.id]}
          editing={!notices[member.id] || replacing.has(member.id)}
          locked={deciding || !open}
          onEditingChange={(on) => setMemberReplacing(member.id, on)}
          onRecorded={keepNotice}
        />
      ))}

      <DecisionSummary
        householdId={draft.id}
        status={draft.status}
        statusReason={draft.status_reason}
        replacing={replacing.size > 0}
        adultMembers={adultMembers}
        notices={notices}
      />

      <Group gap="sm">
        <Button variant="outline" component={Link} to={`/staff/walk-in/${draft.id}`}>
          {t("staff.walkInNotices.backToFile")}
        </Button>
      </Group>
    </Stack>
  );
}

interface NoticeCardProps {
  householdId: string;
  member: Member;
  today: string;
  recorded: RecordedNotice | undefined;
  /** The form is open: no notice yet, or the saved one is being replaced. */
  editing: boolean;
  /** Approval is running or done: the notice can no longer change. */
  locked: boolean;
  onEditingChange: (editing: boolean) => void;
  onRecorded: (notice: RecordedNotice) => void;
}

/** One adult: the notice values, or "did not file" with a reason. */
function NoticeCard({
  householdId,
  member,
  today,
  recorded,
  editing,
  locked,
  onEditingChange,
  onRecorded,
}: NoticeCardProps) {
  const { t } = useTranslation();
  const language = useLanguage();
  const form = useForm<NoticeValues>({ initialValues: EMPTY_NOTICE });
  const [problem, setProblem] = useState<string | null>(null);
  const titleId = `notice-${member.id}`;

  const mutation = useMutation({
    mutationFn: (values: NoticeValues) =>
      recordNotice(householdId, toNoticeInput(member.id, values), language),
    onSuccess: (notice) => {
      onRecorded(notice);
      onEditingChange(false);
    },
    onError: (error) => {
      if (error instanceof WalkInFailed && error.status === 400) {
        const { errors, other } = noticeServerErrors(error.fields);
        form.setErrors(errors);
        setProblem(other.length > 0 ? other.join(" ") : null);
      } else if (error instanceof WalkInFailed) {
        setProblem(error.message || t("staff.walkIn.saveError"));
      } else {
        setProblem(t("staff.walkIn.networkError"));
      }
    },
  });

  const save = () => {
    setProblem(null);
    const errors = noticeErrors(form.values, today);
    form.setErrors(errors);
    if (Object.keys(errors).length === 0) mutation.mutate(form.values);
  };

  const replace = () => {
    form.reset();
    setProblem(null);
    onEditingChange(true);
  };

  const cancel = () => {
    setProblem(null);
    onEditingChange(false);
  };

  const lastYear = Number(today.slice(0, 4)) - 1;

  return (
    <section className={classes.card} aria-labelledby={titleId}>
      <Group justify="space-between" mb="md">
        <Title order={2} id={titleId} className={classes.memberTitle}>
          {fullName(member)}
        </Title>
        {recorded && <StateBadge state={adultState(recorded)} />}
      </Group>

      {problem && (
        <Notice type="error" title={t("staff.walkIn.notSaved")}>
          {problem}
        </Notice>
      )}

      {!editing && recorded ? (
        <Stack gap="sm">
          <RecordedSummary notice={recorded} />
          <Group>
            <Button variant="subtle" onClick={replace} disabled={locked}>
              {t("staff.walkInNotices.replace")}
            </Button>
          </Group>
        </Stack>
      ) : (
        <Stack gap="md">
          <Checkbox
            {...form.getInputProps("didNotFile", { type: "checkbox" })}
            size="md"
            label={t("staff.walkInNotices.didNotFile")}
            description={t("staff.walkInNotices.didNotFileHelp")}
          />

          {form.values.didNotFile ? (
            <TextField
              {...form.getInputProps("reason")}
              label={t("staff.walkInNotices.reason")}
              multiline
              maxLength={MAX_REASON}
            />
          ) : (
            <>
              <Stack gap="xs">
                <FileButton
                  onChange={(file) => form.setFieldValue("file", file)}
                  accept="image/*"
                  capture="environment"
                >
                  {(buttonProps) => (
                    <Button
                      {...buttonProps}
                      variant="outline"
                      leftSection={<IconCamera size={18} aria-hidden />}
                      style={{ alignSelf: "flex-start" }}
                    >
                      {t("staff.walkInNotices.takePhoto")}
                    </Button>
                  )}
                </FileButton>
                <FileUpload
                  {...form.getInputProps("file")}
                  label={t("staff.walkInNotices.file")}
                  accept={NOTICE_TYPES}
                  maxMb={NOTICE_MAX_MB}
                  buttonLabel={t("staff.walkInNotices.chooseFile")}
                />
              </Stack>

              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <IntegerField
                  {...form.getInputProps("taxYear")}
                  label={t("staff.walkInNotices.taxYear")}
                  min={FIRST_TAX_YEAR}
                  max={lastYear}
                />
                <MoneyField
                  {...form.getInputProps("totalIncomeCents")}
                  label={t("staff.walkInNotices.totalIncome")}
                />
                <TextField
                  {...form.getInputProps("nameOnNotice")}
                  label={t("staff.walkInNotices.nameOnNotice")}
                  autoComplete="off"
                />
                <PostalCodeField
                  {...form.getInputProps("postalCodeOnNotice")}
                  label={t("staff.walkInNotices.postalCodeOnNotice")}
                />
                <DateField
                  {...form.getInputProps("noticeDate")}
                  label={t("staff.walkInNotices.noticeDate")}
                  maxDate={today}
                />
              </SimpleGrid>

              <Checkbox
                {...form.getInputProps("seenInPerson", { type: "checkbox" })}
                size="md"
                label={t("staff.walkIn.noticeSeenInPerson")}
                description={t("staff.walkInNotices.seenHelp")}
              />
            </>
          )}

          <Group>
            <Button loading={mutation.isPending} onClick={save} disabled={locked}>
              {t("staff.walkInNotices.save")}
            </Button>
            {recorded && (
              <Button variant="subtle" onClick={cancel} disabled={mutation.isPending}>
                {t("staff.walkInNotices.cancel")}
              </Button>
            )}
          </Group>
        </Stack>
      )}
    </section>
  );
}

const STATE_LABELS: Record<AdultState, string> = {
  missing: "staff.walkInNotices.stateMissing",
  filed: "staff.walkInNotices.stateFiled",
  notSeen: "staff.walkInNotices.stateNotSeen",
  didNotFile: "staff.walkInNotices.stateDidNotFile",
};

const STATE_COLORS: Record<AdultState, string> = {
  missing: "gray",
  filed: "green",
  notSeen: "yellow",
  didNotFile: "yellow",
};

function StateBadge({ state }: { state: AdultState }) {
  const { t } = useTranslation();
  return (
    <Badge color={STATE_COLORS[state]} variant="light">
      {t(STATE_LABELS[state])}
    </Badge>
  );
}

/** What was recorded, so staff can check it before the decision. */
function RecordedSummary({ notice }: { notice: RecordedNotice }) {
  const { t, i18n } = useTranslation();
  if (notice.did_not_file_reason) {
    return (
      <Text size="sm">
        {t("staff.walkInNotices.reason")}: {notice.did_not_file_reason}
      </Text>
    );
  }
  const language = i18n.resolvedLanguage === "en" ? "en" : "fr";
  return (
    <List size="sm" spacing={4}>
      <List.Item>
        {t("staff.walkInNotices.taxYear")}: {notice.tax_year}
      </List.Item>
      <List.Item>
        {t("staff.walkInNotices.totalIncome")}:{" "}
        {formatMoney(notice.total_income_cents ?? 0, language)}
      </List.Item>
      <List.Item>
        {t("staff.walkInNotices.nameOnNotice")}: {notice.name_on_notice}
      </List.Item>
      <List.Item>
        {t("staff.walkInNotices.noticeDate")}: {notice.notice_date}
      </List.Item>
    </List>
  );
}

interface DecisionSummaryProps {
  householdId: string;
  /** draft: submit first; submitted or review_required: approve; anything else is decided. */
  status: string;
  statusReason: string;
  /** A saved notice is being replaced: the old values must not reach the decision. */
  replacing: boolean;
  adultMembers: Member[];
  notices: Record<string, RecordedNotice>;
}

/** Each adult's state, the submit or approve button, then the decision. */
function DecisionSummary({
  householdId,
  status,
  statusReason,
  replacing,
  adultMembers,
  notices,
}: DecisionSummaryProps) {
  const { t } = useTranslation();
  const language = useLanguage();
  const queryClient = useQueryClient();
  const complete = readyForDecision(adultMembers, notices);
  const ready = complete && !replacing;
  const review = ready && needsReview(adultMembers.map((member) => notices[member.id]));
  const [problem, setProblem] = useState<string | null>(null);
  const [submitProblem, setSubmitProblem] = useState<string | null>(null);
  const failureText = (error: Error) => {
    if (!(error instanceof WalkInFailed)) return t("staff.walkIn.networkError");
    const messages = Object.values(error.fields).flat();
    return messages.length > 0 ? messages.join(" ") : error.message;
  };

  const submission = useMutation({
    mutationKey: submitMutationKey(householdId),
    mutationFn: () => submitWalkIn(householdId, language),
    onSuccess: () => {
      setSubmitProblem(null);
      // Reload the file: its new status unlocks the approve button.
      void queryClient.invalidateQueries({ queryKey: walkInQueryKey(householdId) });
    },
    onError: (error) => setSubmitProblem(failureText(error)),
  });

  const mutation = useMutation({
    mutationKey: approveMutationKey(householdId),
    mutationFn: () => approveWalkIn(householdId, language),
    onSuccess: () => {
      setProblem(null);
      // The file is no longer a draft: reload it so the page says so.
      void queryClient.invalidateQueries({ queryKey: walkInQueryKey(householdId) });
    },
    onError: (error) => setProblem(failureText(error)),
  });
  const decision = mutation.data;
  const possibleDuplicate =
    status === "review_required" && statusReason.includes("POSSIBLE_DUPLICATE");

  return (
    <section className={classes.card} aria-labelledby="decision-summary">
      <Title order={2} id="decision-summary" className={classes.memberTitle} mb="sm">
        {t("staff.walkInNotices.summaryTitle")}
      </Title>
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
      {!complete && <Text c="gray.7">{t("staff.walkInNotices.notReady")}</Text>}
      {complete && replacing && <Text c="gray.7">{t("staff.walkInNotices.finishReplacing")}</Text>}
      {ready && !review && (
        <Group gap="xs">
          <IconCircleCheck size={20} aria-hidden />
          <Text>{t("staff.walkInNotices.ready")}</Text>
        </Group>
      )}
      {review && <Notice type="warning" title={t("staff.walkInNotices.review")} />}

      {submitProblem && (
        <Notice type="error" title={t("staff.walkInNotices.notSubmitted")}>
          {submitProblem}
        </Notice>
      )}
      {problem && (
        <Notice type="error" title={t("staff.walkInNotices.notDecided")}>
          {problem}
        </Notice>
      )}
      {!decision && possibleDuplicate && (
        <Notice type="warning" title={t("staff.walkInNotices.possibleDuplicate")} />
      )}
      {decision ? (
        <DecisionOutcome decision={decision} />
      ) : status === "draft" ? (
        <Stack gap={4} mt="md" align="flex-start">
          <Button
            onClick={() => submission.mutate()}
            loading={submission.isPending}
            disabled={!ready}
          >
            {t("staff.walkInNotices.submit")}
          </Button>
          <Text size="sm" c="gray.7">
            {t("staff.walkInNotices.submitHelp")}
          </Text>
        </Stack>
      ) : (
        (status === "submitted" || status === "review_required") && (
          <Stack gap={4} mt="md" align="flex-start">
            <Button
              onClick={() => mutation.mutate()}
              loading={mutation.isPending}
              disabled={!ready}
            >
              {t("staff.walkInNotices.approve")}
            </Button>
            <Text size="sm" c="gray.7">
              {t("staff.walkInNotices.approveHelp")}
            </Text>
          </Stack>
        )
      )}
    </section>
  );
}

const REASON_KEYS: Record<string, string> = {
  INCOME_ABOVE_LICO: "staff.walkInNotices.reasonIncomeAboveLico",
  NAME_MISMATCH: "staff.walkInNotices.reasonNameMismatch",
  ADDRESS_MISMATCH: "staff.walkInNotices.reasonAddressMismatch",
  NOTICE_NOT_SEEN: "staff.walkInNotices.reasonNoticeNotSeen",
  DID_NOT_FILE: "staff.walkInNotices.reasonDidNotFile",
  TAX_YEAR_NOT_ACCEPTED: "staff.walkInNotices.reasonTaxYear",
  IDENTITY_NOT_VERIFIED: "staff.walkInNotices.reasonIdentity",
  INCOME_NOT_CONFIRMED: "staff.walkInNotices.reasonIncomeNotConfirmed",
  REVIEW_REQUIRED: "staff.walkInNotices.reasonReview",
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

/** Approved until a date, rejected with its reason, or sent to review with its reasons. */
function DecisionOutcome({ decision }: { decision: WalkInDecision }) {
  const { t } = useTranslation();
  const language = useLanguage();
  if (decision.status === "approved") {
    const until = decision.expires_at
      ? new Intl.DateTimeFormat(language === "en" ? "en-CA" : "fr-CA", {
          dateStyle: "long",
          timeZone: "America/Montreal",
        }).format(new Date(decision.expires_at))
      : "";
    return (
      <Notice type="success" title={t("staff.walkInNotices.approved", { date: until })}>
        {t("staff.walkInNotices.approvedHelp")}
      </Notice>
    );
  }
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
