// AI contribution: 50% or more AI-generated
import { Button, Group, Modal, Paper, Stack, Text, Textarea, Title } from "@mantine/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import {
  changeHouseholdStatus,
  getStaffHousehold,
  HouseholdStatusFailed,
} from "../../../features/households/statusApi";
import type { StaffHousehold } from "../../../features/households/statusApi";
import { ErrorState, LoadingState, Notice, StatusBadge } from "../../../shared/ui";

type Action = "suspend" | "reactivate";
type ActionModalProps = {
  action: Action | null;
  close: () => void;
  error: unknown;
  pending: boolean;
  reason: string;
  reasonMaxLength: number;
  setReason: (value: string) => void;
  submit: () => void;
};

/** Show the contact and server-provided expiry details. */
function ContactCard({ file }: { file: StaffHousehold }) {
  const { t, i18n } = useTranslation();
  return (
    <Paper withBorder p="md">
      <Stack gap="xs">
        <Title order={2} size="h3">
          {t("household.manage.contact")}
        </Title>
        <Text>{file.email || t("household.search.notProvided")}</Text>
        <Text>{file.phone}</Text>
        {file.expires_at && (
          <Text>
            {t("household.manage.expires", {
              date: new Date(file.expires_at).toLocaleDateString(i18n.language, {
                timeZone: "America/Montreal",
              }),
            })}
          </Text>
        )}
      </Stack>
    </Paper>
  );
}

/** Show the holder identity and lifecycle status. */
function HouseholdHeader({ file }: { file: StaffHousehold }) {
  const { t } = useTranslation();
  const holder = file.members.find((member) => member.relation === "holder");
  return (
    <Group justify="space-between" align="flex-start">
      <div>
        <Title>
          {holder ? `${holder.first_name} ${holder.last_name}` : t("household.manage.title")}
        </Title>
        <Text c="dimmed">{file.member_number || t("household.search.noMemberNumber")}</Text>
      </div>
      <StatusBadge record="household" status={file.status} />
    </Group>
  );
}

/** Show the current reason and the latest successful action. */
function StatusAlerts({ file, outcome }: { file: StaffHousehold; outcome: string | null }) {
  return (
    <>
      {outcome && <Notice type="success">{outcome}</Notice>}
      {file.status_reason && (
        <Notice type={file.status === "suspended" ? "error" : "warning"}>
          {file.status_reason}
        </Notice>
      )}
    </>
  );
}

/** Render only the action authorized by the backend. */
function ActionCard({ action, open }: { action: Action | null; open: (value: Action) => void }) {
  const { t } = useTranslation();
  if (!action) return null;
  return (
    <Paper withBorder p="md">
      <Stack align="flex-start">
        <Title order={2} size="h3">
          {t("household.manage.actions")}
        </Title>
        <Text>{t("household.manage.actionHelp")}</Text>
        <Button
          color={action === "suspend" ? "danger" : "info"}
          variant="outline"
          onClick={() => open(action)}
        >
          {t(`household.manage.${action}`)}
        </Button>
      </Stack>
    </Paper>
  );
}

/** Collect a reason and show field or generic action errors. */
function ActionModal({
  action,
  close,
  error,
  pending,
  reason,
  reasonMaxLength,
  setReason,
  submit,
}: ActionModalProps) {
  const { t } = useTranslation();
  const fieldError = error instanceof HouseholdStatusFailed ? error.fields.reason?.[0] : null;
  return (
    <Modal
      opened={action !== null}
      onClose={close}
      title={action ? t(`household.manage.${action}Title`) : ""}
    >
      <Stack>
        <Textarea
          label={t("household.manage.reason")}
          value={reason}
          maxLength={reasonMaxLength}
          required
          error={fieldError}
          onChange={(event) => setReason(event.currentTarget.value)}
        />
        {Boolean(error) && !fieldError && (
          <Notice type="error">{t("household.manage.failed")}</Notice>
        )}
        <Group justify="flex-end">
          <Button variant="subtle" onClick={close}>
            {t("household.manage.cancel")}
          </Button>
          <Button
            color={action === "suspend" ? "danger" : "info"}
            loading={pending}
            disabled={!reason.trim()}
            onClick={submit}
          >
            {action ? t(`household.manage.${action}`) : ""}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

/** Own clean modal state and the status mutation lifecycle. */
function useStatusForm(id: string) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [action, setAction] = useState<Action | null>(null);
  const [reason, setReason] = useState("");
  const [outcome, setOutcome] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (values: { action: Action; reason: string }) =>
      changeHouseholdStatus(id, values.action, values.reason, i18n.language === "en" ? "en" : "fr"),
    onSuccess: async (_, values) => {
      setAction(null);
      setReason("");
      setOutcome(t(`household.manage.${values.action}Success`));
      await queryClient.invalidateQueries({ queryKey: ["staff-household", id] });
    },
  });
  const close = () => {
    setAction(null);
    setReason("");
    mutation.reset();
  };
  const open = (value: Action) => {
    setOutcome(null);
    setReason("");
    mutation.reset();
    setAction(value);
  };
  const updateReason = (value: string) => {
    mutation.reset();
    setReason(value);
  };
  return { action, close, mutation, open, outcome, reason, updateReason };
}

/** Render one staff-visible household and its authorized status action. */
export function Household() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const { action, close, mutation, open, outcome, reason, updateReason } = useStatusForm(id);
  const household = useQuery({
    queryKey: ["staff-household", id],
    queryFn: () => getStaffHousehold(id),
    enabled: Boolean(id),
  });
  if (household.isPending) return <LoadingState />;
  if (household.isError || !household.data) {
    return <ErrorState onRetry={() => void household.refetch()} />;
  }

  const file = household.data;
  const allowedAction = file.allowed_actions[0] ?? null;

  return (
    <Stack gap="lg">
      <HouseholdHeader file={file} />

      <StatusAlerts file={file} outcome={outcome} />

      <ContactCard file={file} />
      <ActionCard action={allowedAction} open={open} />

      <Button component={Link} to="/staff/households" variant="subtle">
        {t("household.manage.back")}
      </Button>

      <ActionModal
        action={action}
        close={close}
        error={mutation.error}
        pending={mutation.isPending}
        reason={reason}
        reasonMaxLength={file.reason_max_length}
        setReason={updateReason}
        submit={() => action && mutation.mutate({ action, reason })}
      />
    </Stack>
  );
}
