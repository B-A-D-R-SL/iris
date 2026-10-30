// AI contribution: 50% or more AI-generated
/**
 * Post a listing (US-33, T-05.33.4): one phone-first screen with the defaults of
 * forms-and-fields.md, following the SET-11 "Store - Post a listing" flow.
 * The main action stays at the bottom, within thumb reach.
 */
import {
  Button,
  Checkbox,
  Chip,
  Group,
  Input,
  SegmentedControl,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { TimeInput } from "@mantine/dates";
import { useForm } from "@mantine/form";
import { useMutation, useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { AppBar } from "../../../app/layouts/AppBar";
import { getCategories, type Category } from "../../../features/categories/api";
import { PostingFailed, postListing } from "../../../features/listings/api";
import { DateField, FileUpload, IntegerField, MoneyField, TextField } from "../../../shared/forms";
import { ErrorState, LoadingState, Notice } from "../../../shared/ui";
import { CategoryPicker } from "../components/CategoryPicker";
import classes from "./NewListing.module.css";
import {
  DEFAULT_VALUES,
  LIMITS,
  PHOTO_TYPES,
  listingRules,
  serverErrors,
  toNewListing,
  type ListingFormValues,
  type PickupDay,
} from "./newListingForm";

export function NewListing() {
  const { t } = useTranslation();
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
  });

  return (
    <>
      <AppBar title={t("listing.common.postListing")} />
      {isPending ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState onRetry={() => void refetch()} />
      ) : (
        <NewListingForm categories={data} />
      )}
    </>
  );
}

type Outcome = { type: "published"; title: string } | { type: "refused"; message: string } | null;

function NewListingForm({ categories }: { categories: readonly Category[] }) {
  const { t, i18n } = useTranslation();
  const foodCodes = new Set(categories.filter((c) => c.is_food).map((c) => c.code));
  const isFood = (code: string) => foodCodes.has(code);

  const form = useForm<ListingFormValues>({
    initialValues: DEFAULT_VALUES,
    validate: listingRules(isFood),
  });
  // The error summary appears once publishing has been tried, not while typing.
  const [tried, setTried] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);
  // Bring the notices into view after they render (the button is at the bottom).
  const top = useRef<HTMLDivElement>(null);
  const [scrollRequest, setScrollRequest] = useState(0);
  const showTop = () => setScrollRequest((count) => count + 1);
  useEffect(() => {
    if (scrollRequest > 0) top.current?.scrollIntoView({ block: "start" });
  }, [scrollRequest]);

  const mutation = useMutation({
    mutationFn: (values: ListingFormValues) =>
      postListing(
        toNewListing(values, isFood(values.category)),
        values.photo,
        i18n.resolvedLanguage === "en" ? "en" : "fr",
      ),
    onSuccess: (listing) => {
      form.reset();
      setTried(false);
      setOutcome({ type: "published", title: listing.title });
      showTop();
    },
    onError: (error) => {
      if (error instanceof PostingFailed && error.status === 400) {
        const { errors, other } = serverErrors(error.fields);
        form.setErrors(errors);
        setTried(true);
        setOutcome(other.length > 0 ? { type: "refused", message: other.join(" ") } : null);
      } else {
        const message =
          error instanceof PostingFailed
            ? error.message || t("store.newListing.serverError")
            : t("store.newListing.networkError");
        setOutcome({ type: "refused", message });
      }
      showTop();
    },
  });

  const { values } = form;
  const errorCount = Object.values(form.errors).filter(Boolean).length;
  const today = dayjs();
  const dayLabelId = useId();
  const unitLabelId = useId();
  const pickupTitleId = useId();

  const chooseCategory = (code: string) => {
    form.setFieldValue("category", code);
    // Best before only applies to food: drop a stale error when it disappears.
    if (!isFood(code)) form.clearFieldError("bestBefore");
  };

  return (
    <form
      noValidate
      onSubmit={form.onSubmit(
        (submitted) => {
          setOutcome(null);
          mutation.mutate(submitted);
        },
        () => {
          setTried(true);
          setOutcome(null);
          showTop();
        },
      )}
    >
      <div ref={top} className={classes.top} />
      <Stack gap="lg" p="md">
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

        <FileUpload
          label={t("store.newListing.photo")}
          optional
          accept={PHOTO_TYPES}
          maxMb={LIMITS.photoMaxMb}
          buttonLabel={t("store.newListing.photoButton")}
          {...form.getInputProps("photo")}
        />
        <TextField
          label={t("store.newListing.title")}
          placeholder={t("store.newListing.titlePlaceholder")}
          maxLength={LIMITS.titleMax}
          {...form.getInputProps("title")}
        />
        <CategoryPicker
          label={t("store.newListing.category")}
          categories={categories}
          {...form.getInputProps("category")}
          onChange={chooseCategory}
        />
        <TextField
          label={t("store.newListing.description")}
          optional
          multiline
          maxLength={LIMITS.descriptionMax}
          placeholder={t("store.newListing.descriptionPlaceholder")}
          {...form.getInputProps("description")}
        />
        <IntegerField
          label={t("store.newListing.quantity")}
          description={t("store.newListing.quantityHelp")}
          min={1}
          max={LIMITS.quantityMax}
          {...form.getInputProps("quantity")}
        />
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
            value={values.unit}
            onChange={(unit) => form.setFieldValue("unit", unit as ListingFormValues["unit"])}
          />
        </Input.Wrapper>
        <IntegerField
          label={t("store.newListing.maxPerHousehold")}
          description={t("store.newListing.maxPerHouseholdHelp")}
          min={1}
          max={LIMITS.maxPerHousehold}
          {...form.getInputProps("maxPerHousehold")}
        />

        <Stack component="section" gap="md" aria-labelledby={pickupTitleId}>
          <Title order={2} id={pickupTitleId}>
            {t("store.newListing.pickup")}
          </Title>
          <div>
            <Text id={dayLabelId} className={classes.groupLabel}>
              {t("store.newListing.day")}
            </Text>
            <Chip.Group
              value={values.day}
              onChange={(day) => form.setFieldValue("day", day as PickupDay)}
            >
              <Group gap="xs" role="radiogroup" aria-labelledby={dayLabelId}>
                <Chip value="today" size="md" classNames={{ label: classes.chip }}>
                  {t("store.newListing.today")}
                </Chip>
                <Chip value="tomorrow" size="md" classNames={{ label: classes.chip }}>
                  {t("store.newListing.tomorrow")}
                </Chip>
                <Chip value="other" size="md" classNames={{ label: classes.chip }}>
                  {t("store.newListing.otherDate")}
                </Chip>
              </Group>
            </Chip.Group>
          </div>
          {values.day === "other" && (
            <DateField
              label={t("store.newListing.date")}
              minDate={today.format("YYYY-MM-DD")}
              maxDate={today.add(LIMITS.startMaxDays, "day").format("YYYY-MM-DD")}
              {...form.getInputProps("otherDate")}
            />
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
            <Text size="sm" c="gray.7" mt={4}>
              {t("store.newListing.pickupHelp")}
            </Text>
          </div>
          <div>
            <Text className={classes.groupLabel}>{t("store.newListing.location")}</Text>
            <Text>{t("store.newListing.locationValue")}</Text>
          </div>
        </Stack>

        {/* No minDate: an earlier date stays visible with its explanation (SET-11 step 4a). */}
        {isFood(values.category) && (
          <DateField
            label={t("store.newListing.bestBefore")}
            description={t("store.newListing.bestBeforeHelp")}
            {...form.getInputProps("bestBefore")}
          />
        )}
        <MoneyField
          label={t("store.newListing.estimatedValue")}
          optional
          {...form.getInputProps("estimatedValue")}
        />
        <Checkbox
          size="md"
          label={t("store.newListing.safeAndAllowed")}
          aria-required
          {...form.getInputProps("safeAndAllowed", { type: "checkbox" })}
        />
      </Stack>

      <div className={classes.publishBar}>
        <Button type="submit" fullWidth loading={mutation.isPending}>
          {t("store.newListing.publish")}
        </Button>
      </div>
    </form>
  );
}
