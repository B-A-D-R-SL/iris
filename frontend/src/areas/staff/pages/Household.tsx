// AI contribution: 50% or more AI-generated
import {
  Alert,
  Badge,
  Button,
  Group,
  Modal,
  Paper,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
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
import { householdStatusLabels } from "../../../features/households/searchApi";
import { ErrorState, LoadingState } from "../../../shared/ui";

type Action = "suspend" | "reactivate";
type ActionModalProps = {
  action: Action | null;
  close: () => void;
  error: unknown;
  pending: boolean;
  reason: string;
  setReason: (value: string) => void;
  submit: () => void;
};

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
      <Badge variant="light">{t(householdStatusLabels[file.status])}</Badge>
    </Group>
  );
}

function StatusAlerts({ file, outcome }: { file: StaffHousehold; outcome: string | null }) {
  return (
    <>
      {outcome && <Alert color="green">{outcome}</Alert>}
      {file.status_reason && (
        <Alert color={file.status === "suspended" ? "red" : "yellow"}>{file.status_reason}</Alert>
      )}
    </>
  );
}

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
          color={action === "suspend" ? "red" : "blue"}
          variant="outline"
          onClick={() => open(action)}
        >
          {t(`household.manage.${action}`)}
        </Button>
      </Stack>
    </Paper>
  );
}

function ActionModal({
  action,
  close,
  error,
  pending,
  reason,
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
          maxLength={500}
          required
          error={fieldError}
          onChange={(event) => setReason(event.currentTarget.value)}
        />
        {Boolean(error) && !fieldError && <Alert color="red">{t("household.manage.failed")}</Alert>}
        <Group justify="flex-end">
          <Button variant="subtle" onClick={close}>
            {t("household.manage.cancel")}
          </Button>
          <Button
            color={action === "suspend" ? "red" : "blue"}
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
  return { action, mutation, outcome, reason, setAction, setOutcome, setReason };
}

export function Household() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const { action, mutation, outcome, reason, setAction, setOutcome, setReason } = useStatusForm(id);
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
      <ActionCard
        action={allowedAction}
        open={(value) => {
          setOutcome(null);
          setAction(value);
        }}
      />

      <Button component={Link} to="/staff/households" variant="subtle">
        {t("household.manage.back")}
      </Button>

      <ActionModal
        action={action}
        close={() => setAction(null)}
        error={mutation.error}
        pending={mutation.isPending}
        reason={reason}
        setReason={setReason}
        submit={() => action && mutation.mutate({ action, reason })}
      />
    </Stack>
  );
}
