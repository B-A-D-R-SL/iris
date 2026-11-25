// AI contribution: 50% or more AI-generated
/**
 * Walk-in registration (US-17, T-03.17.4): holder, address, members, review.
 * Layout and style follow Figma W3 (cards, "Save draft", "Draft saved"); the
 * fields follow user story #461, which wins where the wireframe differs.
 * "Continue" checks the step and saves the draft, so staff can always resume.
 */
import { Button, Stack, Stepper, Text, Title } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";

import {
  WalkInFailed,
  getWalkIn,
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
import { useLanguage } from "./useLanguage";
import { useWalkInDraft } from "./useWalkInDraft";
import { STEPS, resumeStep, type Step, type WalkInFormValues } from "./walkInForm";

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
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: false,
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
  const { form, current, view, problem, tried, setStep, show, save, saving } =
    useWalkInDraft(draft);
  const { step, saved } = view;
  const index = STEPS.indexOf(step);
  const top = useRef<HTMLDivElement>(null);
  useEffect(() => {
    top.current?.scrollIntoView?.({ block: "start" });
  }, [step, saved, problem]);

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
        <WalkInHeading draft={current} />
        <WalkInFeedback
          problem={problem}
          errorCount={tried ? Object.values(form.errors).filter(Boolean).length : 0}
        />
        <WalkInSteps form={form} step={step} index={index} onStepChange={setStep} />
        <WalkInActions
          reviewing={step === "review"}
          saving={saving}
          onSaveDraft={() => save({ step, saved: true }, true)}
          onContinue={() => save({ step: STEPS[index + 1], saved: false }, false)}
          onBack={index > 0 ? () => setStep(STEPS[index - 1]) : undefined}
        />
      </Stack>
    </form>
  );
}

function WalkInFeedback({ problem, errorCount }: { problem: string | null; errorCount: number }) {
  const { t } = useTranslation();
  return (
    <>
      {problem && (
        <Notice type="error" title={t("staff.walkIn.notSaved")}>
          {problem}
        </Notice>
      )}
      {errorCount > 0 && (
        <Notice
          type="error"
          title={t(errorCount === 1 ? "shared.form.errorCountOne" : "shared.form.errorCountOther", {
            count: errorCount,
          })}
        >
          {t("staff.walkIn.checkFieldsHelp")}
        </Notice>
      )}
    </>
  );
}

interface StepProps {
  form: UseFormReturnType<WalkInFormValues>;
  step: Step;
  index: number;
  onStepChange: (step: Step) => void;
}

function WalkInSteps({ form, step, index, onStepChange }: StepProps) {
  const { t } = useTranslation();
  return (
    <>
      <Stepper
        active={index}
        onStepClick={(next) => onStepChange(STEPS[next])}
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
        {step === "review" && <ReviewStep values={form.values} onEdit={onStepChange} />}
      </section>
    </>
  );
}

interface ActionProps {
  reviewing: boolean;
  saving: boolean;
  onSaveDraft: () => void;
  onContinue: () => void;
  onBack?: () => void;
}

function WalkInActions({ reviewing, saving, onSaveDraft, onContinue, onBack }: ActionProps) {
  const { t } = useTranslation();
  return (
    <div className={classes.actions}>
      {reviewing ? (
        <Button loading={saving} onClick={onSaveDraft}>
          {t("staff.walkIn.saveDraft")}
        </Button>
      ) : (
        <>
          <Button loading={saving} onClick={onContinue}>
            {t("staff.walkIn.continue")}
          </Button>
          <Button variant="outline" disabled={saving} onClick={onSaveDraft}>
            {t("staff.walkIn.saveDraft")}
          </Button>
        </>
      )}
      {onBack && (
        <Button variant="subtle" onClick={onBack}>
          {t("staff.walkIn.back")}
        </Button>
      )}
    </div>
  );
}

function WalkInHeading({ draft }: { draft: WalkInDraft | null }) {
  const { t } = useTranslation();
  const language = useLanguage();
  return (
    <div>
      <Text className={classes.eyebrow}>{t("staff.walkIn.eyebrow")}</Text>
      <Title order={1}>{t("app.staffNav.walkIn")}</Title>
      <Text c="dimmed">{t("staff.walkIn.description")}</Text>
      {draft && (
        <Text size="sm" c="dimmed" mt={4}>
          {t("staff.walkIn.createdBy", {
            email: draft.created_by_email,
            date: formatDateTime(draft.created_at, language),
          })}
        </Text>
      )}
    </div>
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
