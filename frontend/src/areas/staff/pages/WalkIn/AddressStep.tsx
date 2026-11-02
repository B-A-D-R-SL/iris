// AI contribution: 50% or more AI-generated
import { SimpleGrid } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { useTranslation } from "react-i18next";

import { PostalCodeField, TextField } from "../../../../shared/forms";
import type { WalkInFormValues } from "./walkInForm";

type AddressStepProps = {
  form: UseFormReturnType<WalkInFormValues>;
};

const addressFields = [
  { key: "streetNumber", limit: 10, optional: false },
  { key: "streetName", limit: 120, optional: false },
  { key: "unit", limit: 10, optional: true },
  { key: "city", limit: 80, optional: false },
] as const;

export function AddressStep({ form }: AddressStepProps) {
  const { t } = useTranslation();

  const addressTranslation = "household.registrationAddress";

  return (
    <SimpleGrid spacing="md" cols={{ base: 1, sm: 2 }}>
      {addressFields.map(({ key, limit, optional }) => (
        <TextField
          key={key}
          {...form.getInputProps(key)}
          label={t(`${addressTranslation}.${key}`)}
          maxLength={limit}
          autoComplete="off"
          optional={optional}
          {...(key === "streetNumber" ? { description: t("staff.walkIn.streetNumberHelp") } : {})}
        />
      ))}

      <TextField
        label={t(`${addressTranslation}.province`)}
        value="QC"
        readOnly
        onChange={() => {}}
      />

      <PostalCodeField
        {...form.getInputProps("postalCode")}
        label={t(`${addressTranslation}.postalCode`)}
      />
    </SimpleGrid>
  );
}
