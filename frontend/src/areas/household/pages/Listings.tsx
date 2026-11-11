// AI contribution: 50% or more AI-generated
/**
 * Browse listings (US-36, T-05.36.3), following the H1 "Find and reserve"
 * mockups: filter chips, cards sorted by pickup start, and the not-approved and
 * no-result states. Filters live in the address, so the back arrow of a detail
 * screen returns to the same list. The server decides what is visible.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { AppBar } from "../../../app/layouts/AppBar";
import { BrowseFailed, NOT_APPROVED } from "../../../features/listings/browse";
import { FilterChips, type FilterSheetName } from "../components/FilterChips";
import { FilterSheet } from "../components/FilterSheet";
import { ListingResults } from "../components/ListingResults";
import { NotApproved } from "../components/NotApproved";
import household from "../household.module.css";
import { useBrowse } from "../useBrowse";

export function Listings() {
  const { t } = useTranslation();
  const browse = useBrowse();
  const { filters, listings, update } = browse;
  const [sheet, setSheet] = useState<FilterSheetName | null>(null);
  const notApproved =
    listings.error instanceof BrowseFailed && listings.error.code === NOT_APPROVED;

  return (
    <div className={household.palette}>
      <AppBar title={t("app.householdNav.listings")} />
      {notApproved ? (
        <NotApproved />
      ) : (
        <>
          <FilterChips
            filters={filters}
            categoryName={browse.categoryName}
            storeName={browse.storeName}
            onToggleToday={() => update({ today: !filters.today })}
            onOpen={setSheet}
          />
          <ListingResults listings={listings} filtered={browse.filtered} onClear={browse.clear} />
          <FilterSheet
            opened={sheet === "category"}
            onClose={() => setSheet(null)}
            title={t("household.browse.category")}
            allLabel={t("household.browse.allCategories")}
            groups={browse.categoryGroups}
            value={filters.category}
            onChange={(category) => update({ category })}
          />
          <FilterSheet
            opened={sheet === "store"}
            onClose={() => setSheet(null)}
            title={t("household.browse.store")}
            allLabel={t("household.browse.allStores")}
            groups={browse.storeOptions.length > 0 ? [{ options: browse.storeOptions }] : []}
            emptyText={t("household.browse.noStores")}
            value={filters.store}
            onChange={(store) => update({ store })}
          />
        </>
      )}
    </div>
  );
}
