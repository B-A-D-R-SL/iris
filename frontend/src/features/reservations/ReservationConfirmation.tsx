// AI contribution: 50% or more AI-generated
/**
 * The confirmation after reserving (US-41): the 6-character pickup code, large
 * and easy to read out at the store. The QR code and email come with US-42.
 */
import { Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";

import { Notice } from "../../shared/ui";
import type { Reservation } from "./api";
import classes from "./ReservationConfirmation.module.css";

export interface ReservationConfirmationProps {
  reservation: Reservation;
  title: string;
}

export function ReservationConfirmation({ reservation, title }: ReservationConfirmationProps) {
  const { t } = useTranslation();
  return (
    <Stack gap="md">
      <Notice type="success" title={t("reservation.reserve.done")}>
        {t("reservation.reserve.doneDetail", { quantity: reservation.quantity, title })}
      </Notice>
      <Stack gap={4} align="center">
        <Title order={2} size="h4">
          {t("reservation.confirmation.pickupCode")}
        </Title>
        <Text
          className={classes.code}
          aria-label={t("reservation.reserve.codeSpelled", {
            code: reservation.pickup_code.split("").join(" "),
          })}
        >
          {reservation.pickup_code}
        </Text>
        <Text size="sm" c="dimmed" ta="center">
          {t("reservation.reserve.showCode")}
        </Text>
      </Stack>
    </Stack>
  );
}
