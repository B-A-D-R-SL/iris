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

import { useCurrentUser } from "../../../features/accounts/currentUser";
import {
  changeHouseholdStatus,
  getStaffHousehold,
  HouseholdStatusFailed,
} from "../../../features/households/statusApi";
import { householdStatusLabels } from "../../../features/households/searchApi";
import { ErrorState, LoadingState } from "../../../shared/ui";

type Action = "suspend" | "reactivate";

export function Household() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const currentUser = useCurrentUser();
  const queryClient = useQueryClient();
  const [action, setAction] = useState<Action | null>(null);
  const [reason, setReason] = useState("");
  const [outcome, setOutcome] = useState<string | null>(null);
  const household = useQuery({
    queryKey: ["staff-household", id],
    queryFn: () => getStaffHousehold(id),
    enabled: Boolean(id),
  });
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

  if (household.isPending || currentUser.isPending) return <LoadingState />;
  if (household.isError || currentUser.isError || !household.data || !currentUser.data) {
    return <ErrorState onRetry={() => void household.refetch()} />;
  }

  const file = household.data;
  const holder = file.members.find((member) => member.relation === "holder");
  const canSuspend = currentUser.data.role === "admin" && file.status === "approved";
  const canReactivate = currentUser.data.role === "admin" && file.status === "suspended";
  const fieldError =
    mutation.error instanceof HouseholdStatusFailed ? mutation.error.fields.reason?.[0] : null;

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title>
            {holder ? `${holder.first_name} ${holder.last_name}` : t("household.manage.title")}
          </Title>
          <Text c="dimmed">{file.member_number || t("household.search.noMemberNumber")}</Text>
        </div>
        <Badge variant="light">{t(householdStatusLabels[file.status])}</Badge>
      </Group>

      {outcome && <Alert color="green">{outcome}</Alert>}
      {file.status_reason && (
        <Alert color={file.status === "suspended" ? "red" : "yellow"}>{file.status_reason}</Alert>
      )}

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
                date: new Date(file.expires_at).toLocaleDateString(i18n.language),
              })}
            </Text>
          )}
        </Stack>
      </Paper>

      {(canSuspend || canReactivate) && (
        <Paper withBorder p="md">
          <Stack align="flex-start">
            <Title order={2} size="h3">
              {t("household.manage.actions")}
            </Title>
            <Text>{t("household.manage.actionHelp")}</Text>
            <Button
              color={canSuspend ? "red" : "blue"}
              variant="outline"
              onClick={() => {
                setOutcome(null);
                setAction(canSuspend ? "suspend" : "reactivate");
              }}
            >
              {t(`household.manage.${canSuspend ? "suspend" : "reactivate"}`)}
            </Button>
          </Stack>
        </Paper>
      )}

      <Button component={Link} to="/staff/households" variant="subtle">
        {t("household.manage.back")}
      </Button>

      <Modal
        opened={action !== null}
        onClose={() => setAction(null)}
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
          {mutation.isError && !fieldError && (
            <Alert color="red">{t("household.manage.failed")}</Alert>
          )}
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setAction(null)}>
              {t("household.manage.cancel")}
            </Button>
            <Button
              color={action === "suspend" ? "red" : "blue"}
              loading={mutation.isPending}
              disabled={!reason.trim()}
              onClick={() => action && mutation.mutate({ action, reason })}
            >
              {action ? t(`household.manage.${action}`) : ""}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
