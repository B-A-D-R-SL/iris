// AI contribution: 50% or more AI-generated
import { Checkbox, SimpleGrid } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { useTranslation } from "react-i18next";

import { DateField, PhoneField, TextField } from "../../../../shared/forms";
import { SelectField } from "./SelectField";
import type { WalkInFormValues } from "./walkInForm";

type HolderStepProps = {
  form: UseFormReturnType<WalkInFormValues>;
};

const nameFields = [
  { name: "firstName", translation: "firstName" },
  { name: "lastName", translation: "lastName" },
] as const;

export function HolderStep({ form }: HolderStepProps) {
  const { t } = useTranslation();

  const holderKey = "household.registrationHolder";

  const languageOptions = [
    { value: "fr", label: t("staff.walkIn.languageFr") },
    { value: "en", label: t("staff.walkIn.languageEn") },
  ];

  const identityProps = form.getInputProps("identityChecked", {
    type: "checkbox",
  });

  return (
    <>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        {nameFields.map(({ name, translation }) => (
          <TextField
            key={name}
            label={t(`${holderKey}.${translation}`)}
            autoComplete="off"
            {...form.getInputProps(name)}
          />
        ))}

        <DateField {...form.getInputProps("dateOfBirth")} label={t(`${holderKey}.dateOfBirth`)} />

        <PhoneField {...form.getInputProps("phone")} label={t(`${holderKey}.phone`)} />

        <TextField
          {...form.getInputProps("email")}
          label={t(`${holderKey}.email`)}
          type="email"
          optional
          autoComplete="off"
          description={t("staff.walkIn.emailHelp")}
        />

        <SelectField
          {...form.getInputProps("preferredLanguage")}
          label={t(`${holderKey}.preferredLanguage`)}
          description={t("staff.walkIn.languageHelp")}
          data={languageOptions}
        />
      </SimpleGrid>

      <Checkbox
        {...identityProps}
        mt="lg"
        size="md"
        aria-required
        label={t("staff.walkIn.identityCheckedInPerson")}
        description={t("staff.walkIn.identityHelp")}
      />
    </>
  );
}
