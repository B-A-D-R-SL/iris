// AI contribution: 50% or more AI-generated
/**
 * "C'est réservé!" (US-41), following Figma Household > Find and reserve,
 * H1.5 "Reserved" (108:1304): check mark, title, how to use the code, the
 * 6-character pickup code, what was reserved, then "Voir mes réservations".
 * The page passes what was reserved (item, store, address, window) as
 * `children`. The "Afficher le code QR" button and the "confirmation sent by
 * email" line are US-42; "Voir mes réservations" leads to the US-48 page.
 */
import { Button, Stack, Text, Title } from "@mantine/core";
import { IconCircleCheck } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import type { Reservation } from "./api";
import { PickupCode } from "./PickupCode";
import classes from "./ReservationConfirmation.module.css";

export interface ReservationConfirmationProps {
  reservation: Reservation;
  children?: ReactNode;
}

export function ReservationConfirmation({ reservation, children }: ReservationConfirmationProps) {
  const { t } = useTranslation();
  return (
    <Stack gap="md" className={classes.content}>
      {/* Tabler scales its stroke with the size: 1 at 48 px draws Figma's 2 px line. */}
      <IconCircleCheck size={48} stroke={1} aria-hidden className={classes.check} />
      <Title order={2} className={classes.title}>
        {t("reservation.reserve.done")}
      </Title>
      <Text className={classes.muted}>{t("reservation.reserve.showCode")}</Text>
      <PickupCode code={reservation.pickup_code} />
      {children}
      <Button component={Link} to="/reservations" fullWidth>
        {t("reservation.reserve.myReservations")}
      </Button>
    </Stack>
  );
}
