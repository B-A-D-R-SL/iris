// AI contribution: 50% or more AI-generated
/**
 * Walk-in registration (US-17, T-03.17.4): holder, address, members, review.
 * Layout and style follow Figma W3 (cards, "Save draft", "Draft saved"); the
 * fields follow user story #461, which wins where the wireframe differs.
 * "Continue" checks the step and saves the draft, so staff can always resume.
 */
import { Button, Stack, Stepper, Text, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useParams } from "react-router";

import {
  WalkInFailed,
  createWalkIn,
  getWalkIn,
  updateWalkIn,
  walkInQueryKey,
  type WalkInDraft,
} from "../../../../features/households/walkInApi";
import { ErrorState, LoadingState, Notice } from "../../../../shared/ui";
import { AddressStep } from "./AddressStep";
import { DraftSaved } from "./DraftSaved";
import { HolderStep } from "./HolderStep";
import { MembersStep } from "./MembersStep";
import { ReviewStep } from "./ReviewStep";
import classes from "./WalkIn.module.css";
import {
  DEFAULT_VALUES,
  STEPS,
  fromDraft,
  resumeStep,
  serverErrors,
  stepErrors,
  stepOf,
  toPayload,
  type Step,
  type WalkInFormValues,
} from "./walkInForm";

/** What to show after a save: the next step, or the "Draft saved" screen. */
type After = { step: Step; saved: boolean };

const useLanguage = () => {
  const { i18n } = useTranslation();
  return i18n.resolvedLanguage === "en" ? "en" : "fr";
};

/** /staff/walk-in starts a new file; /staff/walk-in/:id resumes a draft. */
export function WalkIn() {
  const { id } = useParams();
  return <WalkInLoader key={id ?? "new"} id={id} />;
}

function WalkInLoader({ id }: { id: string | undefined }) {
  const { t } = useTranslation();
  const language = useLanguage();
  const query = useQuery({
    queryKey: walkInQueryKey(id ?? "new"),
    queryFn: () => getWalkIn(id ?? "", language),
    enabled: Boolean(id),
    staleTime: Infinity,
  });

  if (!id) return <WalkInForm draft={null} />;
  if (query.isPending) return <LoadingState />;
  if (query.isError) {
    if (query.error instanceof WalkInFailed && query.error.status === 404) {
      return <Notice type="error" title={t("staff.walkIn.notFound")} />;
    }
    return <ErrorState onRetry={() => void query.refetch()} />;
  }
  return <WalkInForm draft={query.data} />;
}

function WalkInForm({ draft }: { draft: WalkInDraft | null }) {
  const { t } = useTranslation();
  const language = useLanguage();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  // After the first save the page moves to /staff/walk-in/:id and says where to continue.
  const arrived = useLocation().state as After | null;

  const [initialValues] = useState<WalkInFormValues>(() =>
    draft ? fromDraft(draft) : DEFAULT_VALUES,
  );
  const form = useForm<WalkInFormValues>({ initialValues });
  const [step, setStep] = useState<Step>(
    arrived?.step ?? (draft ? resumeStep(initialValues) : "holder"),
  );
  const [saved, setSaved] = useState(arrived?.saved ?? false);
  const [current, setCurrent] = useState(draft);
  const [tried, setTried] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const top = useRef<HTMLDivElement>(null);
  useEffect(() => {
    top.current?.scrollIntoView?.({ block: "start" });
  }, [step, saved, problem]);

  const show = ({ step: next, saved: isSaved }: After) => {
    setStep(next);
    setSaved(isSaved);
    setTried(false);
  };

  const mutation = useMutation({
    mutationFn: ({ values }: { values: WalkInFormValues; after: After }) =>
      current
        ? updateWalkIn(current.id, toPayload(values), language)
        : createWalkIn(toPayload(values), language),
    onSuccess: (result, { after }) => {
      queryClient.setQueryData(walkInQueryKey(result.id), result);
      if (!current) {
        navigate(`/staff/walk-in/${result.id}`, { replace: true, state: after });
        return;
      }
      setCurrent(result);
      show(after);
    },
    onError: (error) => {
      if (error instanceof WalkInFailed && error.status === 400) {
        const { errors, other } = serverErrors(error.fields);
        form.setErrors(errors);
        setTried(true);
        setProblem(other.length > 0 ? other.join(" ") : null);
        const first = Object.keys(errors)[0];
        if (first) setStep(stepOf(first));
      } else if (error instanceof WalkInFailed) {
        setProblem(error.message || t("staff.walkIn.saveError"));
      } else {
        setProblem(t("staff.walkIn.networkError"));
      }
    },
  });

  /** Checks the step, then saves; a draft save accepts what may wait (ID check, address). */
  const save = (after: After, forDraft: boolean) => {
    setProblem(null);
    const errors = stepErrors(step, form.values, { forDraft });
    if (Object.keys(errors).length > 0) {
      form.setErrors(errors);
      setTried(true);
      setStep(stepOf(Object.keys(errors)[0]));
      return;
    }
    form.clearErrors();
    mutation.mutate({ values: form.values, after });
  };

  const index = STEPS.indexOf(step);
  const errorCount = Object.values(form.errors).filter(Boolean).length;

  if (saved) {
    return (
      <DraftSaved
        values={form.values}
        onResume={() => show({ step: resumeStep(form.values), saved: false })}
      />
    );
  }

  return (
    <form noValidate onSubmit={(event) => event.preventDefault()}>
      <div ref={top} />
      <Stack gap="lg">
        <div>
          <Text className={classes.eyebrow}>{t("staff.walkIn.eyebrow")}</Text>
          <Title order={1}>{t("app.staffNav.walkIn")}</Title>
          <Text c="dimmed">{t("staff.walkIn.description")}</Text>
          {current && (
            <Text size="sm" c="dimmed" mt={4}>
              {t("staff.walkIn.createdBy", {
                email: current.created_by_email,
                date: formatDateTime(current.created_at, language),
              })}
            </Text>
          )}
        </div>

        {problem && (
          <Notice type="error" title={t("staff.walkIn.notSaved")}>
            {problem}
          </Notice>
        )}
        {tried && errorCount > 0 && (
          <Notice
            type="error"
            title={t(
              errorCount === 1 ? "shared.form.errorCountOne" : "shared.form.errorCountOther",
              {
                count: errorCount,
              },
            )}
          >
            {t("staff.walkIn.checkFieldsHelp")}
          </Notice>
        )}

        <Stepper
          active={index}
          onStepClick={(next) => setStep(STEPS[next])}
          allowNextStepsSelect={false}
          size="sm"
        >
          {STEPS.map((key) => (
            <Stepper.Step key={key} label={t(`staff.walkIn.${stepLabel[key]}`)} />
          ))}
        </Stepper>

        <section className={classes.card} aria-labelledby="walk-in-step-title">
          <Title order={2} id="walk-in-step-title" className={classes.memberTitle} mb="md">
            {`${index + 1}. ${t(`staff.walkIn.${stepLabel[step]}`)}`}
          </Title>
          {step === "holder" && <HolderStep form={form} />}
          {step === "address" && <AddressStep form={form} />}
          {step === "members" && <MembersStep form={form} />}
          {step === "review" && <ReviewStep values={form.values} onEdit={setStep} />}
        </section>

        <div className={classes.actions}>
          {step === "review" ? (
            <Button loading={mutation.isPending} onClick={() => save({ step, saved: true }, true)}>
              {t("staff.walkIn.saveDraft")}
            </Button>
          ) : (
            <>
              <Button
                loading={mutation.isPending}
                onClick={() => save({ step: STEPS[index + 1], saved: false }, false)}
              >
                {t("staff.walkIn.continue")}
              </Button>
              <Button
                variant="outline"
                disabled={mutation.isPending}
                onClick={() => save({ step, saved: true }, true)}
              >
                {t("staff.walkIn.saveDraft")}
              </Button>
            </>
          )}
          {index > 0 && (
            <Button variant="subtle" onClick={() => setStep(STEPS[index - 1])}>
              {t("staff.walkIn.back")}
            </Button>
          )}
        </div>
      </Stack>
    </form>
  );
}

const stepLabel: Record<Step, string> = {
  holder: "stepHolder",
  address: "stepAddress",
  members: "stepMembers",
  review: "stepReview",
};

/** "1 novembre 2026, 14 h 05" in Montréal time, whatever the browser's zone. */
function formatDateTime(iso: string, language: "fr" | "en") {
  return new Intl.DateTimeFormat(language === "en" ? "en-CA" : "fr-CA", {
    dateStyle: "long",
    timeStyle: "short",
    timeZone: "America/Montreal",
  }).format(new Date(iso));
}
