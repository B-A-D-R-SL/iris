// AI contribution: 50% or more AI-generated
/**
 * Store list for admins (US-14, Figma W7.1, W7.2b and W7.4): search by name
 * or address, filter by status, and open a store to edit it. The notice from
 * the edit screen (saved, deactivated, reactivated) shows at the top.
 */
import { Button, Chip, Group, Stack, Text, TextInput, Title, VisuallyHidden } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { IconCheck } from "@tabler/icons-react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router";

import {
  listStores,
  staffStoresKey,
  type StaffStorePage,
  type StaffStoreRow,
  type StoreStatusFilter,
} from "../../../features/stores/adminApi";
import classes from "../../../features/stores/stores.module.css";
import type { StoreNotice } from "../../../features/stores/useStoreSave";
import { EmptyState, ErrorState, LoadingState, Notice, StatusBadge } from "../../../shared/ui";

const KEY = "storeAdmin.list";
const FILTERS: StoreStatusFilter[] = ["all", "active", "inactive"];
const FILTER_KEYS = { all: "filterAll", active: "filterActive", inactive: "filterInactive" };

function address(store: StaffStoreRow): string {
  const unit = store.unit ? `, ${store.unit}` : "";
  return `${store.street_number} ${store.street_name}${unit}`;
}

function StoreNoticeBanner({ notice }: { notice: StoreNotice }) {
  const { t } = useTranslation();
  const body =
    notice.kind === "deactivated"
      ? t(`${KEY}.deactivatedBody`, { listings: notice.listings, households: notice.households })
      : t(`${KEY}.${notice.kind}Body`, { name: notice.name });
  return (
    <Notice type="success" title={t(`${KEY}.${notice.kind}Title`)}>
      {body}
    </Notice>
  );
}

interface FiltersProps {
  search: string;
  status: StoreStatusFilter;
  counts?: StaffStorePage["counts"];
  onSearch: (value: string) => void;
  onStatus: (value: StoreStatusFilter) => void;
}

function StoreFilters({ search, status, counts, onSearch, onStatus }: FiltersProps) {
  const { t } = useTranslation();
  return (
    <Group align="flex-end" gap="md">
      <TextInput
        label={t(`${KEY}.searchLabel`)}
        placeholder={t(`${KEY}.searchPlaceholder`)}
        value={search}
        onChange={(event) => onSearch(event.currentTarget.value)}
        style={{ flex: 1, minWidth: 240 }}
      />
      <Chip.Group value={status} onChange={(value) => onStatus(value as StoreStatusFilter)}>
        <Group gap="xs" role="group" aria-label={t(`${KEY}.filtersLabel`)}>
          {FILTERS.map((filter) => (
            <Chip key={filter} value={filter} icon={<IconCheck size={14} stroke={2} aria-hidden />}>
              {t(`${KEY}.${FILTER_KEYS[filter]}`, { count: counts?.[filter] ?? 0 })}
            </Chip>
          ))}
        </Group>
      </Chip.Group>
    </Group>
  );
}

function StoreRow({ store }: { store: StaffStoreRow }) {
  const { t } = useTranslation();
  return (
    <tr>
      <td className={classes.storeName}>{store.name}</td>
      <td>{address(store)}</td>
      <td>{store.open_listings}</td>
      <td>
        <StatusBadge record="store" status={store.is_active ? "active" : "deactivated"} />
      </td>
      <td>
        <Link
          className={classes.editLink}
          to={`/staff/stores/${store.id}`}
          aria-label={t(`${KEY}.editName`, { name: store.name })}
        >
          {t(`${KEY}.edit`)}
        </Link>
      </td>
    </tr>
  );
}

/** Figma W7.1 column widths (200, 180, 100, 110 and 50 px of 740). */
const COLUMNS = [
  { key: "store", width: "29%" },
  { key: "address", width: "27%" },
  { key: "openListings", width: "15%" },
  { key: "status", width: "17%" },
  { key: "actions", width: "12%" },
] as const;

interface PagerProps {
  data: StaffStorePage;
  page: number;
  /** True while the previous page is shown during loading: its bounds are stale. */
  loading: boolean;
  onPage: (page: number) => void;
}

function Pager({ data, page, loading, onPage }: PagerProps) {
  const { t } = useTranslation();
  return (
    <Group>
      <Button
        variant="default"
        disabled={loading || !data.previous || page <= 1}
        onClick={() => onPage(Math.max(1, page - 1))}
      >
        {t(KEY + ".previous")}
      </Button>
      <Text>{t(KEY + ".page", { page })}</Text>
      <Button variant="default" disabled={loading || !data.next} onClick={() => onPage(page + 1)}>
        {t(KEY + ".next")}
      </Button>
    </Group>
  );
}

function StoreTable({ page, loading, onPage, data }: PagerProps) {
  const { t } = useTranslation();
  return (
    <>
      <div className={classes.tableFrame}>
        <div className={classes.tableScroll}>
          <table className={classes.table}>
            <colgroup>
              {COLUMNS.map(({ key, width }) => (
                <col key={key} style={{ width }} />
              ))}
            </colgroup>
            <thead>
              <tr>
                {COLUMNS.map(({ key }) => (
                  <th key={key} scope="col">
                    {key === "actions" ? (
                      <VisuallyHidden>{t(`${KEY}.actions`)}</VisuallyHidden>
                    ) : (
                      t(`${KEY}.${key}`)
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.results.map((store) => (
                <StoreRow key={store.id} store={store} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {(data.previous || data.next) && (
        <Pager data={data} page={page} loading={loading} onPage={onPage} />
      )}
    </>
  );
}

function useStoreList() {
  const { i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "en" ? "en" : "fr";
  const [search, setSearch] = useState("");
  const [q] = useDebouncedValue(search, 300);
  const [status, setStatus] = useState<StoreStatusFilter>("all");
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: [...staffStoresKey, { q, status, page, language }],
    queryFn: () => listStores({ q, status, page }, language),
    placeholderData: keepPreviousData,
  });
  return { query, search, setSearch, status, setStatus, page, setPage };
}

export function Stores() {
  const { t } = useTranslation();
  const notice = (useLocation().state as { notice?: StoreNotice } | null)?.notice;
  const { query, search, setSearch, status, setStatus, page, setPage } = useStoreList();
  const { data, isPending, isError, isPlaceholderData, refetch } = query;
  return (
    <Stack gap={20}>
      <div className={classes.heading}>
        <Text className={classes.eyebrow}>{t(`${KEY}.eyebrow`)}</Text>
        <Title order={1} className={classes.title}>
          {t("app.staffNav.stores")}
        </Title>
        <Text className={classes.subtitle}>{t(`${KEY}.description`)}</Text>
      </div>
      {notice && <StoreNoticeBanner notice={notice} />}
      <StoreFilters
        search={search}
        status={status}
        counts={data?.counts}
        onSearch={(value) => {
          setSearch(value);
          setPage(1);
        }}
        onStatus={(value) => {
          setStatus(value);
          setPage(1);
        }}
      />
      {isPending ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState onRetry={() => void refetch()} />
      ) : data.results.length === 0 ? (
        <EmptyState title={t(`${KEY}.empty`)} description={t(`${KEY}.emptyDescription`)} />
      ) : (
        <StoreTable data={data} page={page} loading={isPlaceholderData} onPage={setPage} />
      )}
    </Stack>
  );
}
