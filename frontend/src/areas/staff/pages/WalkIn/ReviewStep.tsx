// AI contribution: 50% or more AI-generated
import { Button, Group, Stack, Text, Title } from "@mantine/core";
import { IconPencil } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import classes from "./WalkIn.module.css";
import { hasAddress, relationKey, type Step, type WalkInFormValues } from "./walkInForm";

type ReviewStepProps = {
  values: WalkInFormValues;
  onEdit: (step: Step) => void;
};

type SummaryProps = {
  title: string;
  onEdit: () => void;
  children: ReactNode;
};

/** Summarize each registration section and provide its existing edit action. */
export function ReviewStep({ values, onEdit }: ReviewStepProps) {
  const { t } = useTranslation();

  const walkInKey = "staff.walkIn";
  const relationsKey = "household.registrationMembers.relations";

  const fullName = `${values.firstName} ${values.lastName}`;
  const language = t(
    `${walkInKey}.${values.preferredLanguage === "en" ? "languageEn" : "languageFr"}`,
  );
  const email = values.email.trim() || t(`${walkInKey}.noEmail`);
  const identity = t(`${walkInKey}.${values.identityChecked ? "identityYes" : "identityNo"}`);
  const consent = t(`${walkInKey}.${values.consentGiven ? "consentYes" : "consentNo"}`);

  const unit = values.unit.trim();
  const unitText = unit ? `, ${t("household.registrationAddress.unit")} ${unit}` : "";

  const holderLines = [
    values.dateOfBirth,
    email,
    `${values.phone} · ${language}`,
    identity,
    consent,
  ];

  return (
    <Stack gap="md">
      <Summary title={t(`${walkInKey}.stepHolder`)} onEdit={() => onEdit("holder")}>
        <Text fw={600}>{fullName}</Text>
        {holderLines.map((line, index) => (
          <Text key={index}>{line}</Text>
        ))}
      </Summary>

      <Summary title={t(`${walkInKey}.stepAddress`)} onEdit={() => onEdit("address")}>
        {hasAddress(values) ? (
          <>
            <Text>{`${values.streetNumber} ${values.streetName}${unitText}`}</Text>
            <Text>{`${values.city} (QC) ${values.postalCode}`}</Text>
          </>
        ) : (
          <Text c="dimmed">{t(`${walkInKey}.todoAddress`)}</Text>
        )}
      </Summary>

      <Summary title={t(`${walkInKey}.stepMembers`)} onEdit={() => onEdit("members")}>
        <Text>{t(`${walkInKey}.peopleCount`, { count: values.members.length + 1 })}</Text>
        {values.members.map((member) => (
          <Text key={member.key}>
            {`${member.firstName} ${member.lastName} · ${member.dateOfBirth ?? ""} · `}
            {member.relation && t(`${relationsKey}.${relationKey(member.relation)}`)}
          </Text>
        ))}
      </Summary>
    </Stack>
  );
}

function Summary({ title, onEdit, children }: SummaryProps) {
  const { t } = useTranslation();

  return (
    <section className={classes.card}>
      <Group justify="space-between" mb="xs">
        <Title order={3} className={classes.memberTitle}>
          {title}
        </Title>

        <Button
          variant="subtle"
          leftSection={<IconPencil size={18} stroke={2} aria-hidden />}
          onClick={onEdit}
          aria-label={t("staff.walkIn.editStep", { step: title })}
        >
          {t("staff.walkIn.edit")}
        </Button>
      </Group>

      <Stack gap={2}>{children}</Stack>
    </section>
  );
}
