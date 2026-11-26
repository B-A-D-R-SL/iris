// AI contribution: 50% or more AI-generated
/**
 * Mes réservations (US-48), following Figma Household > Pick up with the code,
 * H2.2 and H2.2a: upcoming reservations with their pickup code first, then the
 * pickup history (date, store, item, quantity, status), 20 at a time. The
 * server decides which reservations are upcoming. "Afficher le code QR" is
 * US-42 and "Annuler la réservation" is US-43.
 */
import { Button, Title } from "@mantine/core";
import { IconShoppingBag, IconTicket } from "@tabler/icons-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { type HistoryEntry, useReservationHistory } from "../../../features/reservations/history";
import { AppBar, EmptyState, ErrorState, LoadingState, Notice } from "../../../shared/ui";
import { ReservationCard } from "../components/ReservationCard";
import household from "../household.module.css";
import classes from "./Reservations.module.css";

export function Reservations() {
  const { t } = useTranslation();
  const history = useReservationHistory();
  return (
    <div className={household.palette}>
      <AppBar title={t("reservation.history.title")} />
      <HistoryContent history={history} />
    </div>
  );
}

type History = ReturnType<typeof useReservationHistory>;

/** Loading, failure, or the two sections with "show more". */
function HistoryContent({ history }: { history: History }) {
  const { t } = useTranslation();

  if (history.isPending) return <LoadingState />;
  // Only a failed first load replaces the page; later failures keep what is shown.
  if (history.isLoadingError) return <ErrorState onRetry={() => void history.refetch()} />;
  // Dates read from when the shown reservations were fetched. The query fetches
  // again when the page comes back into view, so "today" moves with the data.
  const now = new Date(history.dataUpdatedAt);
  const { pages } = history.data;
  const entries = pages.flatMap((page) => page.results);
  const upcoming = entries.filter((entry) => entry.upcoming);
  const past = entries.filter((entry) => !entry.upcoming);
  // The API counts every upcoming reservation, not only the pages loaded here.
  const upcomingCount = pages[pages.length - 1].upcoming_count;

  return (
    <div className={classes.content}>
      <UpcomingSection entries={upcoming} count={upcomingCount} now={now} />
      {past.length > 0 && (
        <EntrySection title={t("reservation.common.pickupHistory")} entries={past} now={now} />
      )}
      <LoadMore history={history} />
    </div>
  );
}

/** "Show more", which also asks again for a page that failed to load. */
function LoadMore({ history }: { history: History }) {
  const { t } = useTranslation();
  if (!history.hasNextPage) return null;
  return (
    <>
      {history.isFetchNextPageError && (
        <Notice type="error">{t("reservation.history.loadMoreFailed")}</Notice>
      )}
      <Button
        variant="outline"
        loading={history.isFetchingNextPage}
        onClick={() => void history.fetchNextPage()}
      >
        {t("reservation.history.loadMore")}
      </Button>
    </>
  );
}

/** The reservations still to pick up, or one clear way to make one (H2.2a). */
function UpcomingSection(props: { entries: HistoryEntry[]; count: number; now: Date }) {
  const { entries, count, now } = props;
  const { t } = useTranslation();
  if (entries.length === 0) {
    return (
      <EmptyState
        icon={IconTicket}
        title={t("reservation.history.emptyTitle")}
        description={t("reservation.history.emptyDescription")}
        action={
          <Button component={Link} to="/listings" leftSection={<IconShoppingBag aria-hidden />}>
            {t("reservation.history.seeListings")}
          </Button>
        }
      />
    );
  }
  const title =
    count === 1
      ? t("reservation.history.upcomingOne")
      : t("reservation.history.upcomingMany", { count });
  return <EntrySection title={title} entries={entries} now={now} />;
}

function EntrySection(props: { title: string; entries: HistoryEntry[]; now: Date }) {
  const { title, entries, now } = props;
  const titleId = useId();
  return (
    <section className={classes.section} aria-labelledby={titleId}>
      <Title order={2} id={titleId} className={classes.sectionTitle}>
        {title}
      </Title>
      <ul className={classes.list}>
        {entries.map((entry) => (
          <li key={entry.id}>
            <ReservationCard entry={entry} now={now} />
          </li>
        ))}
      </ul>
    </section>
  );
}
