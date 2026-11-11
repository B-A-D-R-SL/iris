// AI contribution: 50% or more AI-generated
import { IconCheck, IconChevronDown } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import type { BrowseFilters } from "../../../features/listings/browse";
import classes from "../pages/Listings.module.css";

export type FilterSheetName = "category" | "store";

export interface FilterChipsProps {
  filters: BrowseFilters;
  /** The chosen category's and store's names, shown on their chips. */
  categoryName: string | null;
  storeName: string | null;
  onToggleToday: () => void;
  onOpen: (sheet: FilterSheetName) => void;
}

/** A chip that opens a filter sheet; checked and green once a choice is made (H1.3). */
function SheetChip({
  name,
  label,
  onClick,
}: {
  name: string | null;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={classes.chip}
      data-active={name !== null || undefined}
      aria-haspopup="dialog"
      onClick={onClick}
    >
      {name !== null && <IconCheck size={16} stroke={2} aria-hidden />}
      {name ?? label}
      <IconChevronDown size={16} stroke={2} aria-hidden />
    </button>
  );
}

/** The row of filter chips: today (a toggle), then category and store (sheets). */
export function FilterChips({
  filters,
  categoryName,
  storeName,
  onToggleToday,
  onOpen,
}: FilterChipsProps) {
  const { t } = useTranslation();
  return (
    <div className={classes.filters} role="group" aria-label={t("household.browse.filters")}>
      <button
        type="button"
        className={classes.chip}
        aria-pressed={filters.today}
        onClick={onToggleToday}
      >
        {filters.today && <IconCheck size={16} stroke={2} aria-hidden />}
        {t("household.browse.today")}
      </button>
      <SheetChip
        name={filters.category !== null ? categoryName : null}
        label={t("household.browse.category")}
        onClick={() => onOpen("category")}
      />
      <SheetChip
        name={filters.store !== null ? (storeName ?? t("household.browse.store")) : null}
        label={t("household.browse.store")}
        onClick={() => onOpen("store")}
      />
    </div>
  );
}
