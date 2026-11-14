// AI contribution: 50% or more AI-generated
/**
 * Walk-in notices and decision (US-18, T-03.18.4).
 * One card per adult: photograph the notice with the device camera (or choose
 * a file), type the tax year and line-199 income, or record "did not file"
 * with a reason. The summary below shows what each adult has.
 *
 * Notices are recorded on the draft (BR-DOC-007). Once every adult has one,
 * "Submit the file" runs the US-25 duplicate check; then "Approve the file", after
 * a confirmation, asks the server for the decision (approve_walk_in, #469):
 * eligibility decides between approved, rejected and review (BR-DUP-002).
 * Saved notices are loaded on open, and approval waits while a saved notice is
 * being replaced.
 */
import { Badge, Button, Group, Stack, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import {
  listNotices,
  noticesQueryKey,
  type RecordedNotice,
} from "../../../../features/households/noticeApi";
import {
  WalkInFailed,
  getWalkIn,
  walkInQueryKey,
  type WalkInDraft,
} from "../../../../features/households/walkInApi";
import { formatDate } from "../../../../shared/forms";
import { ErrorState, LoadingState, Notice, StatusBadge } from "../../../../shared/ui";
import { DecisionSummary } from "./DecisionSummary";
import { NoticeCard } from "./NoticeCard";
import { adults, fullName, montrealToday } from "./noticeForm";
import { useDeciding } from "./useDecision";
import { useNoticeEditing } from "./useNoticeEditing";
import { useLanguage } from "./useLanguage";
import classes from "./WalkIn.module.css";

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

/** Name, member number, channel and visit date, the file's status, and who is in the household. */
function NoticesHeader({ draft, adultCount }: { draft: WalkInDraft; adultCount: number }) {
  const { t } = useTranslation();
  const language = useLanguage();
  const holder = draft.members.find((member) => member.relation === "holder");
  const visit = formatDate(draft.created_at, language);
  return (
    <div>
      <Text className={classes.eyebrow}>{t("staff.walkIn.eyebrow")}</Text>
      <Title order={1}>
        {t("staff.walkInNotices.headerTitle", { name: holder ? fullName(holder) : "" })}
      </Title>
      <Text c="dimmed">
        {t("staff.walkInNotices.headerMeta", {
          number: draft.member_number || t("household.search.noMemberNumber"),
          channel: t("staff.walkInNotices.channelWalkIn"),
          date: visit,
        })}
      </Text>
      <Group gap="xs" mt="xs">
        <StatusBadge record="household" status={draft.status} />
        <Badge color="neutral" variant="light">
          {t("staff.walkInNotices.headerCounts", {
            adults: adultCount,
            dependants: draft.members.length - adultCount,
          })}
        </Badge>
      </Group>
      <Text c="dimmed" mt="xs">
        {t("staff.walkInNotices.description")}
      </Text>
    </div>
  );
}

function NoticesPage({ draft, saved }: { draft: WalkInDraft; saved: RecordedNotice[] }) {
  const { t } = useTranslation();
  const [today] = useState(montrealToday);
  const adultMembers = adults(draft.members, today);
  const notices = Object.fromEntries(saved.map((notice) => [notice.member, notice]));
  const { replacing, setMemberReplacing, keepNotice } = useNoticeEditing(draft.id);
  const locked = useDeciding(draft.id) || draft.status !== "draft";

  return (
    <Stack gap="lg">
      <NoticesHeader draft={draft} adultCount={adultMembers.length} />
      {draft.status !== "draft" && <Notice type="info" title={t("staff.walkInNotices.notDraft")} />}
      {adultMembers.length === 0 && (
        <Notice type="error" title={t("staff.walkInNotices.noAdults")} />
      )}
      {adultMembers.map((member, index) => (
        <NoticeCard
          key={member.id}
          householdId={draft.id}
          member={member}
          position={index + 1}
          today={today}
          recorded={notices[member.id]}
          editing={!notices[member.id] || replacing.has(member.id)}
          locked={locked}
          onEditingChange={(on) => setMemberReplacing(member.id, on)}
          onRecorded={keepNotice}
        />
      ))}
      <DecisionSummary
        householdId={draft.id}
        status={draft.status}
        statusReason={draft.status_reason}
        expiresAt={draft.expires_at}
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
