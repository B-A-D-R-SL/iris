// AI contribution: 50% or more AI-generated
/** Publishing a listing (US-33): the request, its outcome on screen, and the failure log (FIX-12). */
import type { UseFormReturnType } from "@mantine/form";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { PostingFailed, postListing } from "../../../features/listings/api";
import { logger } from "../../../shared/logger";
import { serverErrors, toNewListing, type ListingFormValues } from "./newListingForm";

export type Outcome =
  { type: "published"; title: string } | { type: "refused"; message: string } | null;

/**
 * The notices at the top of the form, and bringing them into view once they
 * render. The scroll target is returned apart from the state, so reading the
 * state during render never touches a ref.
 */
export function usePostingFeedback() {
  // The error summary appears once publishing has been tried, not while typing.
  const [tried, setTried] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);
  // The button is at the bottom: scroll back to the notices after they render.
  const top = useRef<HTMLDivElement>(null);
  const [scrollRequest, setScrollRequest] = useState(0);
  useEffect(() => {
    if (scrollRequest > 0) top.current?.scrollIntoView({ block: "start" });
  }, [scrollRequest]);
  const showTop = () => setScrollRequest((count) => count + 1);
  return [{ tried, setTried, outcome, setOutcome, showTop }, top] as const;
}

export type PostingFeedback = ReturnType<typeof usePostingFeedback>[0];

/** Logs a failed post with its status code only: 4xx as a warning, 5xx or no answer as an error. */
function logPostFailure(error: Error) {
  const statusCode = error instanceof PostingFailed ? error.status : null;
  if (statusCode !== null && statusCode < 500) {
    logger.warning("listing_post_failed", { statusCode });
  } else {
    logger.error("listing_post_failed", { statusCode });
  }
}

/** Posts the form's values; shows the published title, or puts the server's refusals on the fields. */
export function useNewListingMutation(
  form: UseFormReturnType<ListingFormValues>,
  isFood: (code: string) => boolean,
  feedback: PostingFeedback,
) {
  const { t, i18n } = useTranslation();
  return useMutation({
    mutationFn: (values: ListingFormValues) =>
      postListing(
        toNewListing(values, isFood(values.category)),
        values.photo,
        i18n.resolvedLanguage === "en" ? "en" : "fr",
      ),
    onSuccess: (listing) => {
      form.reset();
      feedback.setTried(false);
      feedback.setOutcome({ type: "published", title: listing.title });
      feedback.showTop();
    },
    onError: (error) => {
      logPostFailure(error);
      if (error instanceof PostingFailed && error.status === 400) {
        const { errors, other } = serverErrors(error.fields);
        form.setErrors(errors);
        feedback.setTried(true);
        // Nothing to show under a field or on top: still say it was refused.
        const unexplained = other.length === 0 && Object.keys(errors).length === 0;
        const message = unexplained
          ? error.message || t("store.newListing.serverError")
          : other.join(" ");
        feedback.setOutcome(message ? { type: "refused", message } : null);
      } else {
        const message =
          error instanceof PostingFailed
            ? error.message || t("store.newListing.serverError")
            : t("store.newListing.networkError");
        feedback.setOutcome({ type: "refused", message });
      }
      feedback.showTop();
    },
  });
}
