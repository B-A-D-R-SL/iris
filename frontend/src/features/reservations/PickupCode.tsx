// AI contribution: 50% or more AI-generated
/**
 * The 6-character pickup code in its box, as on Figma H1.5 "Reserved" and H2
 * "Mes réservations": shown after reserving (US-41) and on each upcoming
 * reservation (US-48).
 */
import { Text, VisuallyHidden } from "@mantine/core";
import { useTranslation } from "react-i18next";

import classes from "./PickupCode.module.css";

export function PickupCode({ code }: { code: string }) {
  const { t } = useTranslation();
  const spelled = code.split("").join(" ");
  return (
    <div className={classes.codeBox}>
      <Text className={classes.codeLabel}>{t("reservation.confirmation.pickupCode")}</Text>
      {/* A paragraph cannot carry an aria-label, so screen readers get the
          spelled code as hidden text and skip the large visual one. */}
      <Text className={classes.code} aria-hidden>
        {code}
      </Text>
      <VisuallyHidden>{t("reservation.reserve.codeSpelled", { code: spelled })}</VisuallyHidden>
    </div>
  );
}
