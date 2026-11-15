// AI contribution: 50% or more AI-generated
/**
 * The cards of the store edit screen (Figma W7.2): store, address, contact,
 * opening hours and pickup instructions. The status card and the actions
 * live in the page, which owns saving.
 */
import { Group, Stack, Text } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { FieldError, PhoneField, PostalCodeField, TextField } from "../../shared/forms";
import { OpeningHoursField } from "./OpeningHoursField";
import {
  HOURS_INVALID,
  hoursErrors,
  markModified,
  type Day,
  type DayValue,
  type StoreFormValues,
} from "./storeForm";
import classes from "./stores.module.css";

export const INSTRUCTIONS_MAX_LENGTH = 300;
const KEY = "storeAdmin.edit";

type StoreForm = UseFormReturnType<StoreFormValues>;

/** A titled card; ``title`` is the visible heading of its fields. */
export function StoreCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={classes.card} aria-label={title}>
      <Stack gap="sm">
        <Text component="h2" className={classes.cardTitle}>
          {title}
        </Text>
        {children}
      </Stack>
    </section>
  );
}

/** Left column: name, address and contact. */
function IdentityCards({ form, modified }: { form: StoreForm; modified: Set<string> }) {
  const { t } = useTranslation();
  const label = (key: string, field: string) =>
    markModified(t(KEY + "." + key), modified.has(field));
  return (
    <Stack gap="md">
      <StoreCard title={t(`${KEY}.storeCard`)}>
        <TextField
          label={label("name", "name")}
          description={t(`${KEY}.nameHelp`)}
          {...form.getInputProps("name")}
        />
      </StoreCard>
      <StoreCard title={t(`${KEY}.addressCard`)}>
        <Group grow align="flex-start" gap="sm">
          <TextField
            label={label("streetNumber", "street_number")}
            {...form.getInputProps("street_number")}
          />
          <TextField
            label={label("streetName", "street_name")}
            {...form.getInputProps("street_name")}
          />
        </Group>
        <Group grow align="flex-start" gap="sm">
          <TextField label={label("unit", "unit")} optional {...form.getInputProps("unit")} />
          <TextField label={label("city", "city")} {...form.getInputProps("city")} />
        </Group>
        <PostalCodeField
          label={label("postalCode", "postal_code")}
          {...form.getInputProps("postal_code")}
        />
      </StoreCard>
      <StoreCard title={t(`${KEY}.contactCard`)}>
        <PhoneField label={label("phone", "phone")} {...form.getInputProps("phone")} />
        <TextField
          label={label("email", "email")}
          type="email"
          autoComplete="email"
          {...form.getInputProps("email")}
        />
      </StoreCard>
    </Stack>
  );
}

/** Right column: opening hours, pickup instructions, then ``children``. */
function PickupCards({ form, notes, modified, children }: StoreFormCardsProps) {
  const { t } = useTranslation();
  const hoursModified = [...modified].some((field) => field.startsWith("hours."));
  const hoursError = form.errors.hours;
  const dayErrors = hoursError ? hoursErrors(form.values.hours) : {};
  // The client check only marks the grid; its messages come from dayErrors.
  // Anything else is a message from the server.
  const serverHoursError =
    typeof hoursError === "string" && hoursError !== HOURS_INVALID ? hoursError : null;
  const changeDay = (day: Day, value: DayValue) => {
    const hours = { ...form.values.hours, [day]: value };
    form.setFieldValue(`hours.${day}`, value);
    // Once the times are fixed, drop the error so the grid and the
    // "fix N fields" notice update at once (not only on the next save).
    if (hoursError && Object.keys(hoursErrors(hours)).length === 0) {
      form.clearFieldError("hours");
    }
  };
  return (
    <Stack gap="md">
      <StoreCard title={markModified(t("storeAdmin.hours.title"), hoursModified)}>
        <OpeningHoursField
          value={form.values.hours}
          modified={modified}
          notes={notes}
          errors={dayErrors}
          onChange={changeDay}
        />
        {serverHoursError && <FieldError>{serverHoursError}</FieldError>}
      </StoreCard>
      <StoreCard title={t(`${KEY}.instructionsCard`)}>
        <TextField
          label={markModified(t(KEY + ".instructions"), modified.has("pickup_instructions"))}
          optional
          multiline
          maxLength={INSTRUCTIONS_MAX_LENGTH}
          {...form.getInputProps("pickup_instructions")}
        />
      </StoreCard>
      {children}
    </Stack>
  );
}

export interface StoreFormCardsProps {
  form: StoreForm;
  notes?: string | null;
  /** Fields changed but not saved (`name`, `hours.mon`...), marked with "*". */
  modified: Set<string>;
  /** The status card, under the pickup instructions in the right column. */
  children?: ReactNode;
}

export function StoreFormCards(props: StoreFormCardsProps) {
  return (
    <div className={classes.columns}>
      <IdentityCards form={props.form} modified={props.modified} />
      <PickupCards {...props} />
    </div>
  );
}
