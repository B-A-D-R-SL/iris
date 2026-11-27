// AI contribution: 50% or more AI-generated
import { Title } from "@mantine/core";
import { IconBuildingStore, IconClock, IconMapPin } from "@tabler/icons-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";

import type { HistoryEntry } from "../../../features/reservations/history";
import { PickupCode } from "../../../features/reservations/PickupCode";
import { Notice, StatusBadge } from "../../../shared/ui";
import classes from "../pages/Reservations.module.css";
import { useReservationText } from "../useReservationText";

export interface ReservationCardProps {
  entry: HistoryEntry;
  now: Date;
}

/**
 * One reservation (H2.2): item × quantity and status, then store, address and
 * date. The code appears only when the API sends one (upcoming reservations).
 */
export function ReservationCard({ entry, now }: ReservationCardProps) {
  const { t } = useTranslation();
  const text = useReservationText();
  const titleId = useId();

  return (
    <article
      className={classes.card}
      aria-labelledby={titleId}
      data-upcoming={entry.upcoming || undefined}
    >
      <div className={classes.cardHead}>
        <Title order={3} id={titleId} className={classes.cardTitle}>
          {t("reservation.reserve.summary", { title: entry.title, quantity: entry.quantity })}
        </Title>
        <StatusBadge record="reservation" status={entry.status} />
      </div>
      <ul className={classes.facts}>
        <li className={classes.fact}>
          <IconBuildingStore size={16} stroke={1.75} aria-hidden />
          {entry.store.name}
        </li>
        <li className={classes.fact} data-muted>
          <IconMapPin size={16} stroke={1.75} aria-hidden />
          {text.address(entry.store)}
        </li>
        <li className={classes.fact}>
          <IconClock size={16} stroke={1.75} aria-hidden />
          {text.when(entry, now)}
        </li>
      </ul>
      {entry.pickup_code && <PickupCode code={entry.pickup_code} />}
      {entry.status === "cancelled_by_store" && (
        <Notice>{t("reservation.history.cancelledByStore")}</Notice>
      )}
    </article>
  );
}
