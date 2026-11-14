// AI contribution: 50% or more AI-generated
import { Button, Stack, Text, Title } from "@mantine/core";
import { IconCircleCheck } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import type { Pickup, PickupFailed } from "../../../features/reservations/pickupApi";
import { TextField } from "../../../shared/forms";
import { Notice } from "../../../shared/ui";
import { PickupScanner, type ScannerStatus } from "../components/PickupScanner";
import { CODE_LENGTH, isCompleteCode } from "./confirmCode";
import { pickupFactRows } from "./confirmFacts";
import { pickedUpAtText, type DayLabels, type Language } from "./confirmFormat";
import { refusalBodyKey, refusalTitleKey } from "./confirmMessages";
import classes from "./Confirm.module.css";

export function RefusalNotice({ error, language }: { error: PickupFailed; language: Language }) {
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

function CameraHint({ camera }: { camera: ScannerStatus }) {
  const { t } = useTranslation();
  if (camera !== "denied" && camera !== "unavailable") return null;
  const body =
    camera === "denied"
      ? t("reservation.confirm.cameraDenied")
      : t("reservation.confirm.cameraUnavailable");
  return (
    <Notice type="warning" title={t("reservation.confirm.cameraTitle")}>
      {body}
    </Notice>
  );
}

function CodeEntry({
  code,
  codeFieldId,
  busy,
  onCodeChange,
  onLookup,
}: {
  code: string;
  codeFieldId: string;
  busy: boolean;
  onCodeChange: (value: string) => void;
  onLookup: () => void;
}) {
  const { t } = useTranslation();
  return (
    <>
      <div className={classes.codeField}>
        <TextField
          id={codeFieldId}
          label={t("reservation.confirmation.pickupCode")}
          description={t("reservation.confirm.codeHelp", { length: CODE_LENGTH })}
          value={code}
          onChange={onCodeChange}
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
    </>
  );
}

export function ScanStep({
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
  return (
    <Stack gap="md">
      {error && <RefusalNotice error={error} language={language} />}
      <CameraHint camera={camera} />
      <PickupScanner active={!busy} onDetected={onDetected} onStatus={onCamera} />
      {camera === "live" && (
        <Text c="dimmed" size="sm">
          {t("reservation.confirm.scanHint")}
        </Text>
      )}
      <CodeEntry
        code={code}
        codeFieldId={codeFieldId}
        busy={busy}
        onCodeChange={onCodeChange}
        onLookup={onLookup}
      />
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
  dayLabels: DayLabels;
}) {
  const { t } = useTranslation();
  const rows = pickupFactRows(pickup, now, language, dayLabels, t);
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

export function ReviewStep({
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
  dayLabels: DayLabels;
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

export function DoneStep({
  pickup,
  now,
  language,
  dayLabels,
  onAgain,
}: {
  pickup: Pickup;
  now: Date;
  language: Language;
  dayLabels: DayLabels;
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
        <Button type="button" fullWidth variant="outline" component={Link} to="/store/listings/new">
          {t("reservation.confirm.backToToday")}
        </Button>
      </div>
    </Stack>
  );
}
