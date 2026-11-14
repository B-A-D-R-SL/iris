// AI contribution: 50% or more AI-generated
/** The form, the save request and the messages of one adult's notice card (US-18). */
import { useForm } from "@mantine/form";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { recordNotice, type RecordedNotice } from "../../../../features/households/noticeApi";
import { WalkInFailed } from "../../../../features/households/walkInApi";
import {
  EMPTY_NOTICE,
  noticeErrors,
  noticeServerErrors,
  toNoticeInput,
  type Member,
  type NoticeValues,
} from "./noticeForm";
import { useLanguage } from "./useLanguage";

interface Options {
  householdId: string;
  member: Member;
  today: string;
  onEditingChange: (editing: boolean) => void;
  onRecorded: (notice: RecordedNotice) => void;
}

/** Field messages for the form, and what to show above the card (null: the fields say it). */
function describeFailure(error: Error, t: (key: string) => string) {
  if (!(error instanceof WalkInFailed))
    return { fields: {}, problem: t("staff.walkIn.networkError") };
  if (error.status !== 400) {
    return { fields: {}, problem: error.message || t("staff.walkIn.saveError") };
  }
  const { errors, other } = noticeServerErrors(error.fields);
  // A 400 without field messages (e.g. a parse error) still explains itself.
  const none = Object.keys(error.fields).length === 0;
  const problem = other.length > 0 ? other.join(" ") : none ? t("staff.walkIn.saveError") : null;
  return { fields: errors, problem };
}

export function useNoticeCard({
  householdId,
  member,
  today,
  onEditingChange,
  onRecorded,
}: Options) {
  const { t } = useTranslation();
  const language = useLanguage();
  const form = useForm<NoticeValues>({ initialValues: EMPTY_NOTICE });
  const [problem, setProblem] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (values: NoticeValues) =>
      recordNotice(householdId, toNoticeInput(member.id, values), language),
    onSuccess: (notice) => {
      onRecorded(notice);
      onEditingChange(false);
    },
    onError: (error) => {
      const failure = describeFailure(error, t);
      form.setErrors(failure.fields);
      setProblem(failure.problem);
    },
  });

  const save = () => {
    setProblem(null);
    const errors = noticeErrors(form.values, today);
    form.setErrors(errors);
    if (Object.keys(errors).length === 0) mutation.mutate(form.values);
  };

  const open = (editing: boolean) => {
    setProblem(null);
    onEditingChange(editing);
  };
  const replace = () => {
    form.reset();
    open(true);
  };

  return { form, problem, saving: mutation.isPending, save, replace, cancel: () => open(false) };
}
