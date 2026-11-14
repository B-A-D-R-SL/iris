// AI contribution: 50% or more AI-generated
import type { Pickup } from "../../../features/reservations/pickupApi";
import {
  pickedUpAtText,
  pickupWindowText,
  unitLabel,
  type DayLabels,
  type Language,
} from "./confirmFormat";

/** Label/value rows for the review and success summaries. */
export function pickupFactRows(
  pickup: Pickup,
  now: Date,
  language: Language,
  dayLabels: DayLabels,
  t: (key: string) => string,
): { label: string; value: string }[] {
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
  return rows;
}
