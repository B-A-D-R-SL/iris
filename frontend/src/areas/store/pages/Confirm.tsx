// AI contribution: 50% or more AI-generated
/**
 * Confirm pickup by camera scan or typed code (US-44, T-06.44.3). Follows the
 * SET-11 "Store - Confirm a pickup" flow: scan → review → one-tap confirm.
 */
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { AppBar } from "../../../shared/ui";
import type { ScannerStatus } from "../components/PickupScanner";
import { ConfirmFlow } from "./ConfirmFlow";
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
        <ConfirmFlow
          flow={flow}
          camera={camera}
          codeFieldId={codeFieldId}
          language={language}
          dayLabels={dayLabels}
          onCamera={setCamera}
        />
      </div>
    </>
  );
}
