// AI contribution: 50% or more AI-generated
import { useForm, type FormErrors, type UseFormReturnType } from "@mantine/form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router";

import {
  WalkInFailed,
  createWalkIn,
  updateWalkIn,
  walkInQueryKey,
  type WalkInDraft,
} from "../../../../features/households/walkInApi";
import { useLanguage } from "./useLanguage";
import {
  DEFAULT_VALUES,
  fromDraft,
  resumeStep,
  serverErrors,
  stepErrors,
  stepOf,
  toPayload,
  withSavedMemberIds,
  type Step,
  type WalkInFormValues,
} from "./walkInForm";

type DraftView = { step: Step; saved: boolean };
type SaveRequest = { values: WalkInFormValues; after: DraftView };

interface SaveOptions {
  current: WalkInDraft | null;
  form: UseFormReturnType<WalkInFormValues>;
  onSaved: (draft: WalkInDraft, after: DraftView) => void;
  onInvalid: (errors: FormErrors, message: string | null) => void;
  setProblem: (message: string | null) => void;
}

function useSaveDraft({ current, form, onSaved, onInvalid, setProblem }: SaveOptions) {
  const { t } = useTranslation();
  const language = useLanguage();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ values }: SaveRequest) =>
      current
        ? updateWalkIn(current.id, toPayload(values, { includeMemberIds: true }), language)
        : createWalkIn(toPayload(values), language),
    onSuccess: (result, { values, after }) => {
      queryClient.setQueryData(walkInQueryKey(result.id), result);
      if (!current) {
        navigate(`/staff/walk-in/${result.id}`, { replace: true, state: after });
        return;
      }
      form.setFieldValue("members", (members) =>
        withSavedMemberIds(members, values.members, result),
      );
      onSaved(result, after);
    },
    onError: (error) => {
      if (error instanceof WalkInFailed && error.status === 400) {
        const { errors, other } = serverErrors(error.fields);
        onInvalid(errors, other.length > 0 ? other.join(" ") : null);
      } else if (error instanceof WalkInFailed) {
        setProblem(error.message || t("staff.walkIn.saveError"));
      } else {
        setProblem(t("staff.walkIn.networkError"));
      }
    },
  });
}

export function useWalkInDraft(draft: WalkInDraft | null) {
  // After creating a draft, the new route carries the next screen.
  const arrived = useLocation().state as DraftView | null;
  const [initialValues] = useState(() => (draft ? fromDraft(draft) : DEFAULT_VALUES));
  const form = useForm<WalkInFormValues>({ initialValues });
  const [view, setView] = useState<DraftView>(
    arrived ?? { step: draft ? resumeStep(initialValues) : "holder", saved: false },
  );
  const [current, setCurrent] = useState(draft);
  const [tried, setTried] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const setStep = (step: Step) => setView((previous) => ({ ...previous, step }));

  const show = (next: DraftView) => {
    setView(next);
    setTried(false);
  };
  const onInvalid = (errors: FormErrors, message: string | null) => {
    form.setErrors(errors);
    setTried(true);
    setProblem(message);
    const first = Object.keys(errors)[0];
    if (first) setStep(stepOf(first));
  };
  const mutation = useSaveDraft({
    current,
    form,
    onInvalid,
    setProblem,
    onSaved(result, after) {
      setCurrent(result);
      show(after);
    },
  });

  const save = (after: DraftView, forDraft: boolean) => {
    setProblem(null);
    const errors = stepErrors(view.step, form.values, { forDraft });
    if (Object.keys(errors).length > 0) {
      onInvalid(errors, null);
      return;
    }
    form.clearErrors();
    mutation.mutate({ values: form.values, after });
  };

  return { form, current, view, problem, tried, setStep, show, save, saving: mutation.isPending };
}
