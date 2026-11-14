// AI contribution: 50% or more AI-generated
/** Requests behind the decision summary: the numbers, submit and approve (US-18). */
import { useIsMutating, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  approveWalkIn,
  decisionSummaryQueryKey,
  getDecisionSummary,
  submitWalkIn,
} from "../../../../features/households/noticeApi";
import { WalkInFailed, walkInQueryKey } from "../../../../features/households/walkInApi";
import { useLanguage } from "./useLanguage";

const approveMutationKey = (householdId: string) => ["walk-in", householdId, "approve"] as const;
const submitMutationKey = (householdId: string) => ["walk-in", householdId, "submit"] as const;

/** Submitting or approving is running: the notices cannot change meanwhile. */
export function useDeciding(householdId: string): boolean {
  const approving = useIsMutating({ mutationKey: approveMutationKey(householdId) });
  const submitting = useIsMutating({ mutationKey: submitMutationKey(householdId) });
  return approving + submitting > 0;
}

export function useDecision(householdId: string) {
  const { t } = useTranslation();
  const language = useLanguage();
  const queryClient = useQueryClient();
  const [problem, setProblem] = useState<string | null>(null);
  const [submitProblem, setSubmitProblem] = useState<string | null>(null);

  const failureText = (error: Error) => {
    if (!(error instanceof WalkInFailed)) return t("staff.walkIn.networkError");
    const messages = Object.values(error.fields).flat();
    return messages.length > 0 ? messages.join(" ") : error.message;
  };
  // The file has a new status: reload it and the numbers the API works out from it.
  const reload = () => {
    void queryClient.invalidateQueries({ queryKey: walkInQueryKey(householdId) });
    void queryClient.invalidateQueries({ queryKey: decisionSummaryQueryKey(householdId) });
  };

  const summary = useQuery({
    queryKey: decisionSummaryQueryKey(householdId),
    queryFn: () => getDecisionSummary(householdId, language),
  });
  const submission = useMutation({
    mutationKey: submitMutationKey(householdId),
    mutationFn: () => submitWalkIn(householdId, language),
    onSuccess: () => {
      setSubmitProblem(null);
      reload();
    },
    onError: (error) => setSubmitProblem(failureText(error)),
  });
  const approval = useMutation({
    mutationKey: approveMutationKey(householdId),
    mutationFn: () => approveWalkIn(householdId, language),
    onSuccess: () => {
      setProblem(null);
      reload();
    },
    onError: (error) => setProblem(failureText(error)),
  });
  return { summary: summary.data, submission, approval, problem, submitProblem };
}
