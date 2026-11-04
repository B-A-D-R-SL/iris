// AI contribution: 50% or more AI-generated
import { Button, Group, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { IconPlus, IconTrash } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { DateField, FieldError, TextField } from "../../../../shared/forms";
import { SelectField } from "./SelectField";
import classes from "./WalkIn.module.css";
import {
  MAX_OTHER_MEMBERS,
  RELATIONS,
  emptyMember,
  relationKey,
  type WalkInFormValues,
} from "./walkInForm";

type MembersStepProps = {
  form: UseFormReturnType<WalkInFormValues>;
};

const nameFields = ["firstName", "lastName"] as const;

export function MembersStep({ form }: MembersStepProps) {
  const { t } = useTranslation();

  const membersKey = "household.registrationMembers";

  const { members, firstName, lastName } = form.values;
  const holderName = `${firstName} ${lastName}`.trim();
  const isFull = members.length >= MAX_OTHER_MEMBERS;

  const relationOptions = RELATIONS.map((relation) => ({
    value: relation,
    label: t(`${membersKey}.relations.${relationKey(relation)}`),
  }));

  return (
    <Stack gap="md">
      <Text>{t("staff.walkIn.holderIsPersonOne", { name: holderName })}</Text>

      {members.length === 0 && <Text c="gray.7">{t("staff.walkIn.noOtherPeople")}</Text>}

      {members.map((member, index) => {
        const number = index + 2;
        const path = `members.${index}`;
        const titleId = `${member.key}-title`;

        return (
          <section key={member.key} className={classes.member} aria-labelledby={titleId}>
            <Group justify="space-between" mb="sm">
              <Title order={3} id={titleId} className={classes.memberTitle}>
                {t("staff.walkIn.personNumber", { number })}
              </Title>

              <Button
                variant="subtle"
                leftSection={<IconTrash size={18} stroke={2} aria-hidden />}
                onClick={() => form.removeListItem("members", index)}
              >
                {t("staff.walkIn.removePerson", { number })}
              </Button>
            </Group>

            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              {nameFields.map((name) => (
                <TextField
                  key={name}
                  {...form.getInputProps(`${path}.${name}`)}
                  label={t(`${membersKey}.${name}`)}
                  autoComplete="off"
                />
              ))}

              <DateField
                {...form.getInputProps(`${path}.dateOfBirth`)}
                label={t(`${membersKey}.dateOfBirth`)}
              />

              <SelectField
                {...form.getInputProps(`${path}.relation`)}
                label={t(`${membersKey}.relation`)}
                data={relationOptions}
              />
            </SimpleGrid>
          </section>
        );
      })}

      {typeof form.errors.members === "string" && <FieldError>{form.errors.members}</FieldError>}

      <div>
        <Button
          variant="outline"
          leftSection={<IconPlus size={18} stroke={2} aria-hidden />}
          disabled={isFull}
          onClick={() => form.insertListItem("members", emptyMember())}
        >
          {t("staff.walkIn.addPerson")}
        </Button>

        {isFull && (
          <Text size="sm" c="gray.7" mt={4}>
            {t("staff.walkIn.maxPeople")}
          </Text>
        )}
      </div>
    </Stack>
  );
}
