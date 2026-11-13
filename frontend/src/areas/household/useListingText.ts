// AI contribution: 50% or more AI-generated
import { useTranslation } from "react-i18next";

import type { Category } from "../../features/categories/api";
import type { ListingCard } from "../../features/listings/browse";
import { formatDate, formatPickupWindow, type Language } from "./listingFormat";

/** The words of a listing card, in the current language, for the list and the detail. */
export function useListingText() {
  const { t, i18n } = useTranslation();
  const language: Language = i18n.resolvedLanguage === "en" ? "en" : "fr";
  const labels = { today: t("household.browse.today"), tomorrow: t("household.browse.tomorrow") };

  return {
    language,

    pickupWindow: (card: ListingCard, now: Date) => formatPickupWindow(card, now, language, labels),

    /** "7 restants", "1 lot restant": bundles say so, items are just counted. */
    unitsLeft: (card: ListingCard) => {
      const bundle = card.unit === "bundle";
      if (card.units_left === 1) {
        return t(bundle ? "household.browse.bundleLeft" : "household.browse.unitLeft");
      }
      return t(bundle ? "household.browse.bundlesLeft" : "household.browse.unitsLeft", {
        count: card.units_left,
      });
    },

    /** "Meilleur avant 11 oct." on a card, "Meilleur avant le 11 oct. 2026" on the detail. */
    bestBefore: (card: ListingCard, detail = false) =>
      card.best_before
        ? t(detail ? "household.listingDetail.bestBefore" : "household.browse.bestBefore", {
            date: formatDate(card.best_before, language, detail),
          })
        : null,

    /** The category's name in this language, or its code until the names have loaded. */
    categoryName: (code: string, categories: readonly Category[] | undefined) => {
      const category = categories?.find((candidate) => candidate.code === code);
      if (!category) return code;
      return language === "en" ? category.name_en : category.name_fr;
    },
  };
}
