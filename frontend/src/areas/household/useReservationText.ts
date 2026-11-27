// AI contribution: 50% or more AI-generated
import { useTranslation } from "react-i18next";

import type { HistoryEntry } from "../../features/reservations/history";
import {
  addDays,
  formatAddress,
  formatPickupWindow,
  formatShortDay,
  formatTime,
  montrealDate,
  type Language,
} from "./listingFormat";

export type PickedUpWhen =
  { day: "today" | "yesterday"; time: string } | { day: "date"; date: string; time: string };

/** When a pickup was confirmed, in Montreal time: today, yesterday or a short date, and the time. */
export function pickedUpWhen(moment: Date, now: Date, language: Language): PickedUpWhen {
  const time = formatTime(moment, language);
  const day = montrealDate(moment);
  const today = montrealDate(now);
  if (day === today) return { day: "today", time };
  if (day === addDays(today, -1)) return { day: "yesterday", time };
  return { day: "date", date: formatShortDay(moment, language), time };
}

/** The words of a reservation card in the pickup history (US-48), in the current language. */
export function useReservationText() {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.resolvedLanguage === "en" ? "en" : "fr";
  const labels = {
    today: t("household.browse.today"),
    tomorrow: t("household.browse.tomorrow"),
    yesterday: t("reservation.history.yesterday"),
  };

  /** "Récupérée hier à 17 h 20" once picked up; otherwise the pickup window. */
  const when = (entry: HistoryEntry, now: Date): string => {
    if (!entry.picked_up_at) return formatPickupWindow(entry, now, language, labels);
    const picked = pickedUpWhen(new Date(entry.picked_up_at), now, language);
    if (picked.day === "date") {
      return t("reservation.history.pickedUpOn", { date: picked.date, time: picked.time });
    }
    const key = picked.day === "today" ? "pickedUpToday" : "pickedUpYesterday";
    return t(`reservation.history.${key}`, { time: picked.time });
  };

  /** "1234, rue Exemple, Montréal H2X 1Y4", with the store's unit when it has one. */
  const address = (store: HistoryEntry["store"]): string =>
    formatAddress(
      store,
      store.unit ? t("household.listingDetail.unit", { unit: store.unit }) : null,
    );

  return { when, address };
}
