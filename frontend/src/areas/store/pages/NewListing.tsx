// AI contribution: 50% or more AI-generated
/**
 * Post a listing (US-33, T-05.33.4): one phone-first screen with the defaults of
 * forms-and-fields.md, following the SET-11 "Store - Post a listing" flow.
 * The main action stays at the bottom, within thumb reach.
 */
import { Button, Stack } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { AppBar } from "../../../app/layouts/AppBar";
import type { Category } from "../../../features/categories/api";
import { getPostingCategories } from "../../../features/listings/api";
import { ErrorState, LoadingState } from "../../../shared/ui";
import {
  ConfirmSection,
  DetailsSection,
  PhotoSection,
  PickupWindowSection,
  PostingNotices,
} from "../components/NewListingSections";
import classes from "./NewListing.module.css";
import { DEFAULT_VALUES, listingRules, type ListingFormValues } from "./newListingForm";
import { useNewListingMutation, usePostingFeedback } from "./useNewListingMutation";

export function NewListing() {
  const { t } = useTranslation();
  // Only the categories this store may post in: prohibited ones never appear (US-34).
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["listings", "categories"],
    queryFn: getPostingCategories,
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

/** The posting form: its sections, the notices on top and the publish bar at the bottom. */
function NewListingForm({ categories }: { categories: readonly Category[] }) {
  const { t } = useTranslation();
  const foodCodes = new Set(categories.filter((c) => c.is_food).map((c) => c.code));
  const isFood = (code: string) => foodCodes.has(code);
  const form = useForm<ListingFormValues>({
    initialValues: DEFAULT_VALUES,
    validate: listingRules(isFood),
  });
  const [feedback, top] = usePostingFeedback();
  const mutation = useNewListingMutation(form, isFood, feedback);

  const chooseCategory = (code: string) => {
    form.setFieldValue("category", code);
    // Best before only applies to food: drop a stale error when it disappears.
    if (!isFood(code)) form.clearFieldError("bestBefore");
  };
  const publish = (submitted: ListingFormValues) => {
    feedback.setOutcome(null);
    mutation.mutate(submitted);
  };
  const showErrors = () => {
    feedback.setTried(true);
    feedback.setOutcome(null);
    feedback.showTop();
  };

  return (
    <form noValidate onSubmit={form.onSubmit(publish, showErrors)}>
      <div ref={top} className={classes.top} />
      <Stack gap="lg" p="md">
        <PostingNotices
          outcome={feedback.outcome}
          tried={feedback.tried}
          errorCount={Object.values(form.errors).filter(Boolean).length}
        />
        <PhotoSection form={form} />
        <DetailsSection form={form} categories={categories} onCategory={chooseCategory} />
        <PickupWindowSection form={form} />
        <ConfirmSection form={form} isFood={isFood(form.values.category)} />
      </Stack>
      <div className={classes.publishBar}>
        <Button type="submit" fullWidth loading={mutation.isPending}>
          {t("store.newListing.publish")}
        </Button>
      </div>
    </form>
  );
}
