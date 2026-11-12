// AI contribution: 50% or more AI-generated
/**
 * Confirm pickup by camera scan or typed code (US-44, T-06.44.3). Follows the
 * SET-11 "Store - Confirm a pickup" flow: scan → review → one-tap confirm.
 */
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { AppBar } from "../../../app/layouts/AppBar";
import type { ScannerStatus } from "../components/PickupScanner";
import { DoneStep, ReviewStep, ScanStep } from "./ConfirmSteps";
import type { Language } from "./confirmFormat";
import { useConfirmPickup } from "./useConfirmPickup";
import classes from "./Confirm.module.css";

function languageOf(resolved: string | undefined): Language {
  return resolved === "en" ? "en" : "fr";
}

export function Confirm() {
  const { t, i18n } = useTranslation();
  const language = languageOf(i18n.resolvedLanguage);
  const [camera, setCamera] = useState<ScannerStatus>("starting");
  const codeFieldId = useId();
  const flow = useConfirmPickup(language);
  const dayLabels = {
    today: t("store.newListing.today"),
    tomorrow: t("store.newListing.tomorrow"),
  };

  return (
    <>
      <AppBar title={t("reservation.common.confirmPickup")} />
      <div className={classes.page}>
        {flow.step.kind === "scan" && (
          <ScanStep
            code={flow.step.code}
            error={flow.step.error}
            camera={camera}
            busy={flow.busy}
            codeFieldId={codeFieldId}
            language={language}
            onCamera={setCamera}
            onDetected={flow.onDetected}
            onCodeChange={flow.setScanCode}
            onLookup={() => flow.requestLookup(flow.step.kind === "scan" ? flow.step.code : "")}
          />
        )}
        {flow.step.kind === "review" && (
          <ReviewStep
            pickup={flow.step.pickup}
            now={flow.now}
            language={language}
            dayLabels={dayLabels}
            busy={flow.busy}
            error={flow.confirmError}
            onConfirm={() => {
              if (flow.step.kind === "review") flow.confirmPickup(flow.step.pickup);
            }}
            onCancel={flow.resetScan}
          />
        )}
        {flow.step.kind === "done" && (
          <DoneStep
            pickup={flow.step.pickup}
            now={flow.now}
            language={language}
            dayLabels={dayLabels}
            onAgain={flow.resetScan}
          />
        )}
      </div>
    </>
  );
}
