// AI contribution: 50% or more AI-generated
/**
 * Listing detail and reserve (US-36 T-05.36.3, US-41 T-06.41.4), following the
 * H1 mockup steps 4 and 5. Until the detail endpoint exists it shows what the
 * browse card holds, so the description, the total quantity and the pickup
 * instructions wait for it. After reserving, the confirmation replaces the
 * listing on this page; a refusal shows a notice at the top (4a, 4b).
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
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useParams } from "react-router";

import { AppBar } from "../../../app/layouts/AppBar";
import { getCategories } from "../../../features/categories/api";
import {
  BrowseFailed,
  NOT_APPROVED,
  useListingCard,
  type ListingCard,
} from "../../../features/listings/browse";
import type { Reservation } from "../../../features/reservations/api";
import { RefusalNotice } from "../../../features/reservations/RefusalNotice";
import { ReservationConfirmation } from "../../../features/reservations/ReservationConfirmation";
import { ReserveButton } from "../../../features/reservations/ReserveButton";
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
  muted,
  children,
}: {
  icon: TablerIcon;
  strong?: boolean;
  muted?: boolean;
  children: ReactNode;
}) {
  return (
    <li className={classes.fact} data-strong={strong || undefined} data-muted={muted || undefined}>
      <Icon size={20} stroke={2} aria-hidden />
      <span>{children}</span>
    </li>
  );
}

/** The store's address, with its unit when it has one. */
function useAddress(card: ListingCard) {
  const { t } = useTranslation();
  const unit = card.store.unit
    ? t("household.listingDetail.unit", { unit: card.store.unit })
    : null;
  return formatAddress(card.store, unit);
}

/** H1.4 "Info": store, address, window, best-before, units left and the household maximum. */
function ListingFacts({ card, now }: { card: ListingCard; now: Date }) {
  const { t } = useTranslation();
  const text = useListingText();
  const bestBefore = text.bestBefore(card, true);
  const max = t("household.listingDetail.maxPerHousehold", { max: card.max_per_household });
  return (
    <ul className={classes.facts}>
      <Fact icon={IconBuildingStore}>{card.store.name}</Fact>
      <Fact icon={IconMapPin} muted>
        {useAddress(card)}
      </Fact>
      <Fact icon={IconClock} strong>
        {text.pickupWindow(card, now)}
      </Fact>
      {bestBefore && <Fact icon={IconCalendar}>{bestBefore}</Fact>}
      <Fact icon={IconPackage}>{`${text.unitsLeft(card)} · ${max}`}</Fact>
    </ul>
  );
}

/** H1.5 "Info": what was reserved, then the store, address and window. */
function ReservedFacts(props: { card: ListingCard; quantity: number; now: Date }) {
  const { card, quantity, now } = props;
  const { t } = useTranslation();
  const text = useListingText();
  return (
    <ul className={classes.facts} data-compact>
      <Fact icon={IconPackage} strong>
        {t("reservation.reserve.summary", { title: card.title, quantity })}
      </Fact>
      <Fact icon={IconBuildingStore}>{card.store.name}</Fact>
      <Fact icon={IconMapPin} muted>
        {useAddress(card)}
      </Fact>
      <Fact icon={IconClock}>{text.pickupWindow(card, now)}</Fact>
    </ul>
  );
}

/** H1.4: the listing, a refusal notice at the top, and the sticky Reserve actions. */
function ListingView(props: {
  card: ListingCard;
  now: Date;
  onReserved: (r: Reservation) => void;
}) {
  const { card, now, onReserved } = props;
  const text = useListingText();
  const categories = useQuery({ queryKey: ["categories"], queryFn: getCategories });
  const [refusal, setRefusal] = useState<string | null>(null);
  return (
    <>
      <Stack gap="md" className={classes.content}>
        {refusal && <RefusalNotice code={refusal} />}
        <ListingPhoto url={card.photo_url} size="large" />
        <Stack gap={6} align="flex-start">
          <Title order={2} className={classes.title}>
            {card.title}
          </Title>
          <span className={classes.category}>
            {text.categoryName(card.category, categories.data)}
          </span>
        </Stack>
        <ListingFacts card={card} now={now} />
      </Stack>
      <div className={classes.actions}>
        <ReserveButton
          listingId={card.id}
          maxPerHousehold={card.max_per_household}
          unitsLeft={card.units_left}
          onReserved={onReserved}
          onRefused={setRefusal}
        />
      </div>
    </>
  );
}

interface DetailContentProps {
  listing: ReturnType<typeof useListingCard>;
  backTo: string;
  now: Date;
  reservation: Reservation | null;
  onReserved: (reservation: Reservation) => void;
}

function DetailContent({ listing, backTo, now, reservation, onReserved }: DetailContentProps) {
  const { t } = useTranslation();
  const card = listing.data;
  if (listing.isPending) return <LoadingState />;
  if (listing.error instanceof BrowseFailed && listing.error.code === NOT_APPROVED) {
    return <NotApproved />;
  }
  if (listing.isError) return <ErrorState onRetry={() => void listing.refetch()} />;
  if (reservation && card) {
    return (
      <ReservationConfirmation reservation={reservation}>
        <ReservedFacts card={card} quantity={reservation.quantity} now={now} />
      </ReservationConfirmation>
    );
  }
  if (!card) {
    return (
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
  }
  return <ListingView card={card} now={now} onReserved={onReserved} />;
}

export function ListingDetail() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const location = useLocation();
  const client = useQueryClient();
  const [now] = useState(() => new Date());
  const [reservation, setReservation] = useState<Reservation | null>(null);
  const listing = useListingCard(id);

  // Back to the list as it was, filters included.
  const search = (location.state as { search?: unknown } | null)?.search;
  const backTo = `/listings${typeof search === "string" ? search : ""}`;
  const onReserved = (made: Reservation) => {
    setReservation(made);
    // The list's "units left" changed; this page keeps its card for the summary.
    void client.invalidateQueries({ queryKey: ["listings"] });
  };

  return (
    <div className={household.palette}>
      <AppBar
        title={t(reservation ? "reservation.confirmation.title" : "listing.common.listing")}
        backTo={backTo}
      />
      <DetailContent
        listing={listing}
        backTo={backTo}
        now={now}
        reservation={reservation}
        onReserved={onReserved}
      />
    </div>
  );
}
