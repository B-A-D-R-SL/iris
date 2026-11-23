// AI contribution: 50% or more AI-generated
/**
 * A walk-in household's Iris account (US-93): linked, linkable after an ID check,
 * invited, or not possible. The backend decides the state; this card only shows it.
 */
import { Button, Checkbox, Group, Modal, Paper, Stack, Text, Title } from "@mantine/core";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  HouseholdStatusFailed,
  linkHouseholdAccount,
  resendHouseholdInvitation,
} from "../../../features/households/statusApi";
import type { HouseholdAccount } from "../../../features/households/statusApi";
import { Notice } from "../../../shared/ui";
import { useLanguage } from "./WalkIn/useLanguage";

type Action = "link" | "resend";

interface HouseholdAccountCardProps {
  householdId: string;
  email: string | null;
  holderName: string;
  account: HouseholdAccount;
  /** The query that holds this file, reloaded after a link or a new invitation. */
  reloadKey: readonly unknown[];
}

const STATE_KEYS: Partial<Record<HouseholdAccount["status"], string>> = {
  linked: "household.account.linked",
  can_link: "household.account.canLink",
  invited: "household.account.invited",
  no_email: "household.account.noEmail",
};
const REASON_KEYS: Record<string, string> = {
  not_beneficiary: "household.account.cannotLinkNotBeneficiary",
  inactive: "household.account.cannotLinkInactive",
  has_household: "household.account.cannotLinkHasHousehold",
};

/** The sentence for this state; cannot_link says why. */
function stateKey(account: HouseholdAccount): string {
  if (account.status === "cannot_link") return REASON_KEYS[account.reason] ?? "";
  return STATE_KEYS[account.status] ?? "";
}

/** The server's own message when it gave one, otherwise a generic failure. */
function problemText(error: unknown, fallback: string): string {
  const messages = error instanceof HouseholdStatusFailed ? Object.values(error.fields).flat() : [];
  return messages.length > 0 ? messages.join(" ") : fallback;
}

interface LinkModalProps {
  opened: boolean;
  holderName: string;
  accountName: string;
  pending: boolean;
  problem: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

/** Compare the person's ID with both names, then confirm the check before linking. */
function LinkModal({
  opened,
  holderName,
  accountName,
  pending,
  problem,
  onCancel,
  onConfirm,
}: LinkModalProps) {
  const { t } = useTranslation();
  const [checked, setChecked] = useState(false);
  const close = () => {
    setChecked(false);
    onCancel();
  };
  return (
    <Modal opened={opened} onClose={close} title={t("household.account.linkTitle")}>
      <Stack>
        <Text>{t("household.account.linkHelp")}</Text>
        <Text>{t("household.account.holderOnFile", { name: holderName })}</Text>
        <Text>{t("household.account.nameOnAccount", { name: accountName })}</Text>
        <Checkbox
          label={t("household.account.identityChecked")}
          checked={checked}
          onChange={(event) => setChecked(event.currentTarget.checked)}
        />
        {problem && <Notice type="error">{problem}</Notice>}
        <Group justify="flex-end">
          <Button variant="subtle" onClick={close}>
            {t("household.manage.cancel")}
          </Button>
          <Button loading={pending} disabled={!checked} onClick={onConfirm}>
            {t("household.account.link")}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

/** Link or re-invite, keeping the outcome and the refusal for the card to show. */
function useAccountAction(householdId: string, onChanged: () => void) {
  const { t } = useTranslation();
  const language = useLanguage();
  const [outcome, setOutcome] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (action: Action) =>
      action === "link"
        ? linkHouseholdAccount(householdId, language)
        : resendHouseholdInvitation(householdId, language),
    onSuccess: (_, action) => {
      setOutcome(
        t(action === "link" ? "household.account.linkedSuccess" : "household.account.resent"),
      );
      onChanged();
    },
  });
  const problem = mutation.error
    ? problemText(mutation.error, t("household.account.failed"))
    : null;
  return { mutation, outcome, problem };
}

interface ResendActionProps {
  pending: boolean;
  problem: string | null;
  onResend: () => void;
}

/** A new set-password link, for an email that failed or a link that expired. */
function ResendAction({ pending, problem, onResend }: ResendActionProps) {
  const { t } = useTranslation();
  return (
    <>
      <Text size="sm">{t("household.account.resendHelp")}</Text>
      {problem && <Notice type="error">{problem}</Notice>}
      <Button variant="outline" loading={pending} onClick={onResend}>
        {t("household.account.resend")}
      </Button>
    </>
  );
}

/** The account state, with the one action the backend allows for it. */
export function HouseholdAccountCard(props: HouseholdAccountCardProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [linking, setLinking] = useState(false);
  const { mutation, outcome, problem } = useAccountAction(props.householdId, () => {
    setLinking(false);
    void queryClient.invalidateQueries({ queryKey: props.reloadKey });
  });
  const { account } = props;
  if (account.status === "not_applicable") return null;
  const accountName =
    `${account.account_first_name ?? ""} ${account.account_last_name ?? ""}`.trim();
  const openLink = () => {
    mutation.reset();
    setLinking(true);
  };
  return (
    <Paper withBorder p="md">
      <Stack align="flex-start" gap="xs">
        <Title order={2} size="h3">
          {t("household.account.title")}
        </Title>
        {outcome && <Notice type="success">{outcome}</Notice>}
        <Text>{t(stateKey(account), { email: props.email ?? "" })}</Text>
        {account.status === "invited" && (
          <ResendAction
            pending={mutation.isPending}
            problem={problem}
            onResend={() => mutation.mutate("resend")}
          />
        )}
        {account.status === "can_link" && (
          <Button variant="outline" onClick={openLink}>
            {t("household.account.link")}
          </Button>
        )}
      </Stack>
      <LinkModal
        opened={linking}
        holderName={props.holderName}
        accountName={accountName}
        pending={mutation.isPending}
        problem={linking ? problem : null}
        onCancel={() => setLinking(false)}
        onConfirm={() => mutation.mutate("link")}
      />
    </Paper>
  );
}
