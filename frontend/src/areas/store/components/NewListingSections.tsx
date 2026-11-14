// AI contribution: 50% or more AI-generated
/**
 * The sections of the posting form (US-33, SET-11 "Store - Post a listing"), in
 * screen order: notices, photo, details, pickup window, and the final checks.
 */
import { Checkbox, Chip, Group, Input, SegmentedControl, Stack, Text, Title } from "@mantine/core";
import { TimeInput } from "@mantine/dates";
import type { UseFormReturnType } from "@mantine/form";
import { useId } from "react";
import { useTranslation } from "react-i18next";

import type { Category } from "../../../features/categories/api";
import { DateField, FileUpload, IntegerField, MoneyField, TextField } from "../../../shared/forms";
import { Notice } from "../../../shared/ui";
import classes from "../pages/NewListing.module.css";
import { PHOTO_TYPES, type ListingFormValues, type PickupDay } from "../pages/newListingForm";
import type { Outcome } from "../pages/useNewListingMutation";
import { CategoryPicker } from "./CategoryPicker";
import { ProhibitedItemsLink } from "./ProhibitedItemsLink";

type ListingForm = UseFormReturnType<ListingFormValues>;

interface PostingNoticesProps {
  outcome: Outcome;
  /** Publishing was tried: from then on the fields to fix are counted. */
  tried: boolean;
  errorCount: number;
}

/** The published or refused notice, and the "Vérifiez N champs" summary. */
export function PostingNotices({ outcome, tried, errorCount }: PostingNoticesProps) {
  const { t } = useTranslation();
  return (
    <>
      {outcome?.type === "published" && (
        <Notice type="success" title={t("store.newListing.published")}>
          {t("store.newListing.publishedDescription", { title: outcome.title })}
        </Notice>
      )}
      {outcome?.type === "refused" && (
        <Notice type="error" title={t("store.newListing.notPublished")}>
          {outcome.message}
        </Notice>
      )}
      {tried && errorCount > 0 && (
        <Notice
          type="error"
          title={
            errorCount === 1
              ? t("store.newListing.checkOneField")
              : t("store.newListing.checkFields", { count: errorCount })
          }
        >
          {t("store.newListing.checkFieldsHelp")}
        </Notice>
      )}
    </>
  );
}

export function PhotoSection({ form }: { form: ListingForm }) {
  const { t } = useTranslation();
  return (
    <FileUpload
      label={t("store.newListing.photo")}
      optional
      accept={PHOTO_TYPES}
      buttonLabel={t("store.newListing.photoButton")}
      {...form.getInputProps("photo")}
    />
  );
}

/** Article or Lot, as a two-choice switch labelled by its field label. */
function UnitControl({ form }: { form: ListingForm }) {
  const { t } = useTranslation();
  const unitLabelId = useId();
  return (
    <Input.Wrapper
      label={t("store.newListing.unit")}
      labelElement="div"
      labelProps={{ id: unitLabelId }}
      error={form.errors.unit}
    >
      <SegmentedControl
        fullWidth
        size="md"
        classNames={{ label: classes.segmentedLabel }}
        aria-labelledby={unitLabelId}
        data={[
          { value: "item", label: t("listing.units.item") },
          { value: "bundle", label: t("listing.units.bundle") },
        ]}
        value={form.values.unit}
        onChange={(unit) => form.setFieldValue("unit", unit as ListingFormValues["unit"])}
      />
    </Input.Wrapper>
  );
}

interface DetailsSectionProps {
  form: ListingForm;
  categories: readonly Category[];
  onCategory: (code: string) => void;
}

/** What is offered: title, category, description, quantity, unit and the household limit. */
export function DetailsSection({ form, categories, onCategory }: DetailsSectionProps) {
  const { t } = useTranslation();
  return (
    <>
      <TextField
        label={t("store.newListing.title")}
        placeholder={t("store.newListing.titlePlaceholder")}
        {...form.getInputProps("title")}
      />
      <CategoryPicker
        label={t("store.newListing.category")}
        categories={categories}
        {...form.getInputProps("category")}
        onChange={onCategory}
      />
      <TextField
        label={t("store.newListing.description")}
        optional
        multiline
        placeholder={t("store.newListing.descriptionPlaceholder")}
        {...form.getInputProps("description")}
      />
      <IntegerField
        label={t("store.newListing.quantity")}
        description={t("store.newListing.quantityHelp")}
        {...form.getInputProps("quantity")}
      />
      <UnitControl form={form} />
      <IntegerField
        label={t("store.newListing.maxPerHousehold")}
        description={t("store.newListing.maxPerHouseholdHelp")}
        {...form.getInputProps("maxPerHousehold")}
      />
    </>
  );
}

/** Aujourd'hui, Demain or Autre date, as radio chips labelled "Jour". */
function PickupDayChips({ form }: { form: ListingForm }) {
  const { t } = useTranslation();
  const dayLabelId = useId();
  const days = [
    { value: "today", labelKey: "store.newListing.today" },
    { value: "tomorrow", labelKey: "store.newListing.tomorrow" },
    { value: "other", labelKey: "store.newListing.otherDate" },
  ];
  return (
    <div>
      <Text id={dayLabelId} className={classes.groupLabel}>
        {t("store.newListing.day")}
      </Text>
      <Chip.Group
        value={form.values.day}
        onChange={(day) => form.setFieldValue("day", day as PickupDay)}
      >
        <Group gap="xs" role="radiogroup" aria-labelledby={dayLabelId}>
          {days.map((day) => (
            <Chip key={day.value} value={day.value} size="md" classNames={{ label: classes.chip }}>
              {t(day.labelKey)}
            </Chip>
          ))}
        </Group>
      </Chip.Group>
    </div>
  );
}

/** The pickup window: day, start and end times, and where (the store's address). */
export function PickupWindowSection({ form }: { form: ListingForm }) {
  const { t } = useTranslation();
  const pickupTitleId = useId();
  return (
    <Stack component="section" gap="md" aria-labelledby={pickupTitleId}>
      <Title order={2} id={pickupTitleId}>
        {t("store.newListing.pickup")}
      </Title>
      <PickupDayChips form={form} />
      {form.values.day === "other" && (
        <DateField label={t("store.newListing.date")} {...form.getInputProps("otherDate")} />
      )}
      <div>
        <Group grow align="flex-start" gap="sm">
          <TimeInput
            label={t("store.newListing.start")}
            aria-required
            {...form.getInputProps("startTime")}
          />
          <TimeInput
            label={t("store.newListing.end")}
            aria-required
            {...form.getInputProps("endTime")}
          />
        </Group>
        <Text size="sm" c="dimmed" mt={4}>
          {t("store.newListing.pickupHelp")}
        </Text>
      </div>
      <div>
        <Text className={classes.groupLabel}>{t("store.newListing.location")}</Text>
        <Text>{t("store.newListing.locationValue")}</Text>
      </div>
    </Stack>
  );
}

/** Best before (food only), the estimated value, and the safe-and-allowed confirmation. */
export function ConfirmSection({ form, isFood }: { form: ListingForm; isFood: boolean }) {
  const { t } = useTranslation();
  return (
    <>
      {/* No minDate: an earlier date stays visible with its explanation (SET-11 step 4a). */}
      {isFood && (
        <DateField
          label={t("store.newListing.bestBefore")}
          description={t("store.newListing.bestBeforeHelp")}
          {...form.getInputProps("bestBefore")}
        />
      )}
      <MoneyField
        label={t("store.newListing.estimatedValue")}
        optional
        allowNegative
        {...form.getInputProps("estimatedValue")}
      />
      <div>
        <Checkbox
          size="md"
          label={t("store.newListing.safeAndAllowed")}
          aria-required
          {...form.getInputProps("safeAndAllowed", { type: "checkbox" })}
        />
        {/* Lined up under the checkbox label, as in the SET-11 mockup. */}
        <div className={classes.checkboxLink}>
          <ProhibitedItemsLink />
        </div>
      </div>
    </>
  );
}
