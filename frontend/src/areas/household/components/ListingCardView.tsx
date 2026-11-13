// AI contribution: 50% or more AI-generated
import { Text, Title } from "@mantine/core";
import { IconBuildingStore, IconClock } from "@tabler/icons-react";
import { Link } from "react-router";

import type { ListingCard } from "../../../features/listings/browse";
import classes from "../pages/Listings.module.css";
import { useListingText } from "../useListingText";
import { ListingPhoto } from "./ListingPhoto";

export interface ListingCardViewProps {
  card: ListingCard;
  now: Date;
  /** Router state for the detail screen, so its back arrow keeps the filters. */
  linkState?: unknown;
}

/** One card (H1.2): photo, title, store, pickup window, units left and best-before. */
export function ListingCardView({ card, now, linkState }: ListingCardViewProps) {
  const text = useListingText();
  const bestBefore = text.bestBefore(card);

  return (
    <Link to={`/listings/${card.id}`} state={linkState} className={classes.card}>
      <ListingPhoto url={card.photo_url} size="thumb" />
      <div className={classes.cardBody}>
        <Title order={2} className={classes.cardTitle}>
          {card.title}
        </Title>
        <span className={classes.line} data-muted>
          <IconBuildingStore size={16} stroke={1.75} aria-hidden />
          {card.store.name}
        </span>
        <span className={classes.line}>
          <IconClock size={16} stroke={1.75} aria-hidden />
          {text.pickupWindow(card, now)}
        </span>
        <span className={classes.badge}>{text.unitsLeft(card)}</span>
        {bestBefore && (
          <Text size="xs" c="gray.7">
            {bestBefore}
          </Text>
        )}
      </div>
    </Link>
  );
}
