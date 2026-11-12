// AI contribution: 50% or more AI-generated
/**
 * "C'est réservé!" (US-41), following Figma Household > Find and reserve,
 * H1.5 "Reserved" (108:1304): check mark, title, how to use the code, the
 * 6-character pickup code, what was reserved, then "Voir mes réservations".
 * The page passes what was reserved (item, store, address, window) as
 * `children`. The "Afficher le code QR" button and the "confirmation sent by
 * email" line are US-42; "Voir mes réservations" leads to US-42/US-43's page.
 */
import { Button, Stack, Text, Title } from "@mantine/core";
import { IconCircleCheck } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import type { Reservation } from "./api";
import classes from "./ReservationConfirmation.module.css";

export interface ReservationConfirmationProps {
  reservation: Reservation;
  children?: ReactNode;
}

export function ReservationConfirmation({ reservation, children }: ReservationConfirmationProps) {
  const { t } = useTranslation();
  const spelled = reservation.pickup_code.split("").join(" ");
  return (
    <Stack gap="md" className={classes.content}>
      {/* Tabler scales its stroke with the size: 1 at 48 px draws Figma's 2 px line. */}
      <IconCircleCheck size={48} stroke={1} aria-hidden className={classes.check} />
      <Title order={2} className={classes.title}>
        {t("reservation.reserve.done")}
      </Title>
      <Text className={classes.muted}>{t("reservation.reserve.showCode")}</Text>
      <div className={classes.codeBox}>
        <Text className={classes.codeLabel}>{t("reservation.confirmation.pickupCode")}</Text>
        <Text
          className={classes.code}
          aria-label={t("reservation.reserve.codeSpelled", { code: spelled })}
        >
          {reservation.pickup_code}
        </Text>
      </div>
      {children}
      <Button component={Link} to="/reservations" fullWidth>
        {t("reservation.reserve.myReservations")}
      </Button>
    </Stack>
  );
}
