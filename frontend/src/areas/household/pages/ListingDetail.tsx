// AI contribution: 50% or more AI-generated
/**
 * Listing detail (US-36, T-05.36.3), following the H1.4 mockup. Until the
 * detail endpoint exists it shows what the browse card holds, so the
 * description, the total quantity and the pickup instructions wait for it.
 * Reserving belongs to US-41.
 */
import { Button, Stack, Title } from "@mantine/core";
import {
  IconBuildingStore,
  IconCalendar,
  IconClock,
  IconMapPin,
  IconPackage,
  IconPackageOff,
  type TablerIcon,
} from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useParams } from "react-router";

import { AppBar } from "../../../app/layouts/AppBar";
import { getCategories } from "../../../features/categories/api";
import { BrowseFailed, NOT_APPROVED, useListingCard } from "../../../features/listings/browse";
import { EmptyState, ErrorState, LoadingState } from "../../../shared/ui";
import { ListingPhoto } from "../components/ListingPhoto";
import { NotApproved } from "../components/NotApproved";
import household from "../household.module.css";
import { formatAddress } from "../listingFormat";
import { useListingText } from "../useListingText";
import classes from "./ListingDetail.module.css";

function Fact({
  icon: Icon,
  strong,
  children,
}: {
  icon: TablerIcon;
  strong?: boolean;
  children: ReactNode;
}) {
  return (
    <li className={classes.fact} data-strong={strong || undefined}>
      <Icon size={20} stroke={1.75} aria-hidden />
      <span>{children}</span>
    </li>
  );
}

export function ListingDetail() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const text = useListingText();
  const location = useLocation();
  const [now] = useState(() => new Date());
  const listing = useListingCard(id);
  const categories = useQuery({ queryKey: ["categories"], queryFn: getCategories });

  // Back to the list as it was, filters included.
  const search = (location.state as { search?: unknown } | null)?.search;
  const backTo = `/listings${typeof search === "string" ? search : ""}`;
  const card = listing.data;

  let content: ReactNode;
  if (listing.isPending) {
    content = <LoadingState />;
  } else if (listing.error instanceof BrowseFailed && listing.error.code === NOT_APPROVED) {
    content = <NotApproved />;
  } else if (listing.isError) {
    content = <ErrorState onRetry={() => void listing.refetch()} />;
  } else if (!card) {
    content = (
      <EmptyState
        icon={IconPackageOff}
        title={t("household.listingDetail.goneTitle")}
        description={t("household.listingDetail.goneDescription")}
        action={
          <Button component={Link} to={backTo} variant="outline">
            {t("household.listingDetail.backToListings")}
          </Button>
        }
      />
    );
  } else {
    const bestBefore = text.bestBefore(card, true);
    const unit = card.store.unit
      ? t("household.listingDetail.unit", { unit: card.store.unit })
      : null;
    content = (
      <Stack gap="md" p="md">
        <ListingPhoto url={card.photo_url} size="large" />
        <Stack gap={6} align="flex-start">
          <Title order={2} className={classes.title}>
            {card.title}
          </Title>
          <span className={classes.category}>
            {text.categoryName(card.category, categories.data)}
          </span>
        </Stack>
        <ul className={classes.facts}>
          <Fact icon={IconBuildingStore}>{card.store.name}</Fact>
          <Fact icon={IconMapPin}>{formatAddress(card.store, unit)}</Fact>
          <Fact icon={IconClock} strong>
            {text.pickupWindow(card, now)}
          </Fact>
          {bestBefore && <Fact icon={IconCalendar}>{bestBefore}</Fact>}
          <Fact icon={IconPackage}>{text.unitsLeft(card)}</Fact>
        </ul>
      </Stack>
    );
  }

  return (
    <div className={household.palette}>
      <AppBar title={t("listing.common.listing")} backTo={backTo} />
      {content}
    </div>
  );
}
