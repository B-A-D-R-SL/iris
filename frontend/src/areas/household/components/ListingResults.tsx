// AI contribution: 50% or more AI-generated
import { Button, Stack, Text } from "@mantine/core";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router";

import type { useListings } from "../../../features/listings/browse";
import { EmptyState, ErrorState, LoadingState } from "../../../shared/ui";
import classes from "../pages/Listings.module.css";
import { ListingCardView } from "./ListingCardView";

/** No card to show: suggest clearing the filters (H1.3a), or say new listings come every day. */
function NoListings({ filtered, onClear }: { filtered: boolean; onClear: () => void }) {
  const { t } = useTranslation();
  if (!filtered) {
    return (
      <EmptyState
        title={t("household.browse.emptyTitle")}
        description={t("household.browse.emptyDescription")}
      />
    );
  }
  return (
    <EmptyState
      title={t("household.browse.noMatchTitle")}
      description={t("household.browse.noMatchDescription")}
      action={
        <Button variant="outline" onClick={onClear}>
          {t("household.browse.clearFilters")}
        </Button>
      }
    />
  );
}

export interface ListingResultsProps {
  listings: ReturnType<typeof useListings>;
  filtered: boolean;
  onClear: () => void;
}

/** Loading, failure, nothing to show, or the cards with "show more" (H1.2). */
export function ListingResults({ listings, filtered, onClear }: ListingResultsProps) {
  const { t } = useTranslation();
  const location = useLocation();
  const [now] = useState(() => new Date());

  if (listings.isPending) return <LoadingState />;
  if (listings.isError) return <ErrorState onRetry={() => void listings.refetch()} />;
  const cards = listings.data.pages.flatMap((page) => page.results);
  if (cards.length === 0) return <NoListings filtered={filtered} onClear={onClear} />;
  const count = listings.data.pages[0]?.count ?? 0;

  return (
    <Stack gap="sm" px="md" pb="lg">
      <Text size="sm" c="gray.7">
        {count === 1 ? t("household.browse.countOne") : t("household.browse.countMany", { count })}
      </Text>
      <ul className={classes.list}>
        {cards.map((card) => (
          <li key={card.id}>
            <ListingCardView card={card} now={now} linkState={{ search: location.search }} />
          </li>
        ))}
      </ul>
      {listings.hasNextPage && (
        <Button
          variant="outline"
          loading={listings.isFetchingNextPage}
          onClick={() => void listings.fetchNextPage()}
        >
          {t("household.browse.loadMore")}
        </Button>
      )}
    </Stack>
  );
}
