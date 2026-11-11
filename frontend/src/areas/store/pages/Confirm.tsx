// AI contribution: 50% or more AI-generated
/**
 * Confirm pickup by camera scan or typed code (US-44, T-06.44.3). Follows the
 * SET-11 "Store - Confirm a pickup" flow: scan → review → one-tap confirm.
 */
import { Button, Stack, Text, Title } from "@mantine/core";
import { IconCircleCheck } from "@tabler/icons-react";
import { useMutation } from "@tanstack/react-query";
import { useCallback, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { AppBar } from "../../../app/layouts/AppBar";
import {
  confirmPickup,
  lookupPickup,
  PickupFailed,
  type Pickup,
} from "../../../features/reservations/pickupApi";
import { TextField } from "../../../shared/forms";
import { Notice } from "../../../shared/ui";
import { PickupScanner, type ScannerStatus } from "../components/PickupScanner";
import { CODE_LENGTH, codeFromScan, draftCode, isCompleteCode } from "./confirmCode";
import { pickedUpAtText, pickupWindowText, unitLabel, type Language } from "./confirmFormat";
import { refusalBodyKey, refusalTitleKey } from "./confirmMessages";
import classes from "./Confirm.module.css";

type Step =
  | { kind: "scan"; code: string; error: PickupFailed | null }
  | { kind: "review"; pickup: Pickup }
  | { kind: "done"; pickup: Pickup };

function languageOf(resolved: string | undefined): Language {
  return resolved === "en" ? "en" : "fr";
}

export function Confirm() {
  const { t, i18n } = useTranslation();
  const language = languageOf(i18n.resolvedLanguage);
  const [step, setStep] = useState<Step>({ kind: "scan", code: "", error: null });
  const [camera, setCamera] = useState<ScannerStatus>("starting");
  const [now] = useState(() => new Date());
  const codeFieldId = useId();
  const lookupLock = useRef(false);

  const dayLabels = {
    today: t("store.newListing.today"),
    tomorrow: t("store.newListing.tomorrow"),
  };

  const lookup = useMutation({
    mutationFn: (code: string) => lookupPickup(code, language),
    onSuccess: (pickup) => setStep({ kind: "review", pickup }),
    onError: (error, code) => {
      const failed =
        error instanceof PickupFailed
          ? error
          : new PickupFailed(0, { code: "unavailable", message: "", fields: {} });
      setStep({ kind: "scan", code, error: failed });
    },
    onSettled: () => {
      lookupLock.current = false;
    },
  });

  const confirm = useMutation({
    mutationFn: (pickup: Pickup) => confirmPickup(pickup.id, language),
    onSuccess: (pickup) => setStep({ kind: "done", pickup }),
    onError: (error, pickup) => {
      const failed =
        error instanceof PickupFailed
          ? error
          : new PickupFailed(0, { code: "unavailable", message: "", fields: {} });
      setStep({ kind: "scan", code: pickup.pickup_code, error: failed });
    },
  });

  const busy = lookup.isPending || confirm.isPending;

  const requestLookup = useCallback(
    (raw: string) => {
      const code = draftCode(raw);
      if (!isCompleteCode(code) || lookupLock.current || confirm.isPending) return;
      lookupLock.current = true;
      setStep({ kind: "scan", code, error: null });
      lookup.mutate(code);
    },
    [confirm.isPending, lookup],
  );

  const onDetected = useCallback(
    (text: string) => {
      const code = codeFromScan(text);
      if (!code) return;
      requestLookup(code);
    },
    [requestLookup],
  );

  const resetScan = () => {
    lookupLock.current = false;
    lookup.reset();
    confirm.reset();
    setStep({ kind: "scan", code: "", error: null });
  };

  return (
    <>
      <AppBar title={t("reservation.common.confirmPickup")} />
      <div className={classes.page}>
        {step.kind === "scan" && (
          <ScanStep
            code={step.code}
            error={step.error}
            camera={camera}
            busy={busy}
            codeFieldId={codeFieldId}
            language={language}
            onCamera={setCamera}
            onDetected={onDetected}
            onCodeChange={(value) =>
              setStep({ kind: "scan", code: draftCode(value), error: step.error })
            }
            onLookup={() => requestLookup(step.code)}
          />
        )}
        {step.kind === "review" && (
          <ReviewStep
            pickup={step.pickup}
            now={now}
            language={language}
            dayLabels={dayLabels}
            busy={busy}
            error={confirm.error instanceof PickupFailed ? confirm.error : null}
            onConfirm={() => confirm.mutate(step.pickup)}
            onCancel={resetScan}
          />
        )}
        {step.kind === "done" && (
          <DoneStep
            pickup={step.pickup}
            now={now}
            language={language}
            dayLabels={dayLabels}
            onAgain={resetScan}
          />
        )}
      </div>
    </>
  );
}

function RefusalNotice({ error, language }: { error: PickupFailed; language: Language }) {
  const { t } = useTranslation();
  const when =
    error.code === "already_picked_up" && error.picked_up_at
      ? t("reservation.confirm.alreadyPickedUpAt", {
          time: pickedUpAtText(error.picked_up_at, language),
        })
      : null;
  return (
    <Notice type="error" title={t(refusalTitleKey(error.code))}>
      <Text>{t(refusalBodyKey(error.code))}</Text>
      {when && <Text mt="xs">{when}</Text>}
    </Notice>
  );
}

function ScanStep({
  code,
  error,
  camera,
  busy,
  codeFieldId,
  language,
  onCamera,
  onDetected,
  onCodeChange,
  onLookup,
}: {
  code: string;
  error: PickupFailed | null;
  camera: ScannerStatus;
  busy: boolean;
  codeFieldId: string;
  language: Language;
  onCamera: (status: ScannerStatus) => void;
  onDetected: (text: string) => void;
  onCodeChange: (value: string) => void;
  onLookup: () => void;
}) {
  const { t } = useTranslation();
  const cameraHint =
    camera === "denied"
      ? t("reservation.confirm.cameraDenied")
      : camera === "unavailable"
        ? t("reservation.confirm.cameraUnavailable")
        : t("reservation.confirm.scanHint");

  return (
    <Stack gap="md">
      {error && <RefusalNotice error={error} language={language} />}
      {(camera === "denied" || camera === "unavailable") && (
        <Notice type="warning" title={t("reservation.confirm.cameraTitle")}>
          {cameraHint}
        </Notice>
      )}
      <PickupScanner active={!busy} onDetected={onDetected} onStatus={onCamera} />
      {camera === "live" && (
        <Text c="dimmed" size="sm">
          {t("reservation.confirm.scanHint")}
        </Text>
      )}
      <div className={classes.codeField}>
        <TextField
          id={codeFieldId}
          label={t("reservation.confirmation.pickupCode")}
          description={t("reservation.confirm.codeHelp", { length: CODE_LENGTH })}
          value={code}
          onChange={onCodeChange}
          maxLength={CODE_LENGTH}
          autoComplete="off"
          name="pickup_code"
          disabled={busy}
        />
      </div>
      <Button
        type="button"
        fullWidth
        disabled={!isCompleteCode(code) || busy}
        loading={busy}
        onClick={onLookup}
      >
        {t("reservation.confirm.verify")}
      </Button>
    </Stack>
  );
}

function ReviewStep({
  pickup,
  now,
  language,
  dayLabels,
  busy,
  error,
  onConfirm,
  onCancel,
}: {
  pickup: Pickup;
  now: Date;
  language: Language;
  dayLabels: { today: string; tomorrow: string };
  busy: boolean;
  error: PickupFailed | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Stack gap="md">
      <Title order={2}>{t("reservation.confirm.reviewTitle")}</Title>
      {error && <RefusalNotice error={error} language={language} />}
      <PickupFacts pickup={pickup} now={now} language={language} dayLabels={dayLabels} />
      <div className={classes.actions}>
        <Button type="button" fullWidth loading={busy} onClick={onConfirm}>
          {t("reservation.confirm.confirmHandover")}
        </Button>
        <Button type="button" fullWidth variant="outline" disabled={busy} onClick={onCancel}>
          {t("reservation.confirm.cancel")}
        </Button>
      </div>
    </Stack>
  );
}

function DoneStep({
  pickup,
  now,
  language,
  dayLabels,
  onAgain,
}: {
  pickup: Pickup;
  now: Date;
  language: Language;
  dayLabels: { today: string; tomorrow: string };
  onAgain: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Stack gap="md" align="stretch">
      <div className={classes.successIcon} aria-hidden>
        <IconCircleCheck size={40} stroke={1.75} />
      </div>
      <Notice type="success" title={t("reservation.confirm.successTitle")}>
        {t("reservation.confirm.successBody", {
          name: pickup.holder ?? t("reservation.confirm.unknownHolder"),
        })}
      </Notice>
      <PickupFacts pickup={pickup} now={now} language={language} dayLabels={dayLabels} />
      <div className={classes.actions}>
        <Button type="button" fullWidth onClick={onAgain}>
          {t("reservation.confirm.scanAnother")}
        </Button>
        <Button type="button" fullWidth variant="outline" component={Link} to="/store">
          {t("reservation.confirm.backToToday")}
        </Button>
      </div>
    </Stack>
  );
}

function PickupFacts({
  pickup,
  now,
  language,
  dayLabels,
}: {
  pickup: Pickup;
  now: Date;
  language: Language;
  dayLabels: { today: string; tomorrow: string };
}) {
  const { t } = useTranslation();
  const rows: { label: string; value: string }[] = [
    {
      label: t("reservation.confirm.holder"),
      value: pickup.holder ?? t("reservation.confirm.unknownHolder"),
    },
  ];
  if (pickup.alternate) {
    rows.push({ label: t("reservation.confirm.alternate"), value: pickup.alternate });
  }
  rows.push(
    { label: t("reservation.confirm.item"), value: pickup.title },
    {
      label: t("reservation.confirm.quantity"),
      value: `${pickup.quantity} · ${unitLabel(pickup.unit, t)}`,
    },
    { label: t("reservation.confirmation.pickupCode"), value: pickup.pickup_code },
    {
      label: t("reservation.confirmation.pickupWindow"),
      value: pickupWindowText(pickup, now, language, dayLabels),
    },
  );
  if (pickup.picked_up_at) {
    rows.push({
      label: t("reservation.confirm.pickedUpAt"),
      value: pickedUpAtText(pickup.picked_up_at, language),
    });
  }

  return (
    <dl className={classes.facts}>
      {rows.map((row) => (
        <div key={row.label} className={classes.fact}>
          <dt>{row.label}</dt>
          <dd>{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}
