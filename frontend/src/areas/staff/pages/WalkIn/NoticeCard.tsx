// AI contribution: 50% or more AI-generated
/**
 * One adult's card (US-18): the saved notice, or the form to record it, or "did not
 * file" with a free-text reason (forms-and-fields.md).
 */
import { Button, Group, Stack, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";

import type { RecordedNotice } from "../../../../features/households/noticeApi";
import { Notice } from "../../../../shared/ui";
import { NoticeFields } from "./NoticeFields";
import { RecordedSummary, StateBadge } from "./NoticeSummary";
import { adultState, fullName, type Member } from "./noticeForm";
import { useNoticeCard } from "./useNoticeCard";
import classes from "./WalkIn.module.css";

export interface NoticeCardProps {
  householdId: string;
  member: Member;
  /** 1 for the first adult: Figma titles the card "Adulte 1 · name". */
  position: number;
  today: string;
  recorded: RecordedNotice | undefined;
  /** The form is open: no notice yet, or the saved one is being replaced. */
  editing: boolean;
  /** Approval is running or done: the notice can no longer change. */
  locked: boolean;
  onEditingChange: (editing: boolean) => void;
  onRecorded: (notice: RecordedNotice) => void;
}

export function NoticeCard(props: NoticeCardProps) {
  const { t } = useTranslation();
  const { member, position, recorded, editing, locked } = props;
  const card = useNoticeCard(props);
  const titleId = `notice-${member.id}`;
  const title = t(
    member.relation === "holder"
      ? "staff.walkInNotices.cardTitleHolder"
      : "staff.walkInNotices.cardTitle",
    { number: position, name: fullName(member) },
  );

  return (
    <section className={classes.card} aria-labelledby={titleId}>
      <Group justify="space-between" mb="md">
        <Title order={2} id={titleId} className={classes.memberTitle}>
          {title}
        </Title>
        {recorded && <StateBadge state={adultState(recorded)} />}
      </Group>
      {card.problem && (
        <Notice type="error" title={t("staff.walkIn.notSaved")}>
          {card.problem}
        </Notice>
      )}
      {!editing && recorded ? (
        <Stack gap="sm">
          <RecordedSummary notice={recorded} />
          <Group>
            <Button variant="subtle" onClick={card.replace} disabled={locked}>
              {t("staff.walkInNotices.replace")}
            </Button>
          </Group>
        </Stack>
      ) : (
        <NoticeFields
          form={card.form}
          today={props.today}
          locked={locked}
          saving={card.saving}
          canCancel={Boolean(recorded)}
          onSave={card.save}
          onCancel={card.cancel}
        />
      )}
    </section>
  );
}
