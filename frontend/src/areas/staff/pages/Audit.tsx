// AI contribution: 50% or more AI-generated
import { Button, Group, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { useState, type Dispatch, type FormEvent, type SetStateAction } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "../../../shared/api/generated";
import { EmptyState, ErrorState, LoadingState } from "../../../shared/ui";

type AuditPage = components["schemas"]["PaginatedAuditEventList"];

/** Read only the supported outcome field from audit metadata. */
function getOutcome(metadata: unknown): string | undefined {
  if (
    typeof metadata === "object" &&
    metadata !== null &&
    "outcome" in metadata &&
    typeof metadata.outcome === "string"
  ) {
    return metadata.outcome;
  }
}

interface Filters {
  household: string;
  actor: string;
  from: string;
  to: string;
}
const emptyFilters: Filters = { household: "", actor: "", from: "", to: "" };

/** Fetch and minimally validate one private audit page. */
async function getAuditEvents(filters: Filters, page: number): Promise<AuditPage> {
  const params = new URLSearchParams({ page: String(page) });
  for (const [key, value] of Object.entries(filters)) {
    if (value.trim()) params.set(key, value.trim());
  }
  const response = await fetch(`/api/staff/audit/?${params}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`Audit search failed: ${response.status}`);
  const data: unknown = await response.json();
  if (
    typeof data !== "object" ||
    data === null ||
    !("results" in data) ||
    !Array.isArray(data.results)
  ) {
    throw new Error("Invalid audit search response");
  }
  return data as AuditPage;
}

type FilterFormProps = {
  draft: Filters;
  errors: Partial<Record<keyof Filters, string>>;
  submit: (event: FormEvent) => void;
  update: (key: keyof Filters, value: string) => void;
};

/** Render controlled audit filters without owning query state. */
function AuditFilterForm({ draft, errors, submit, update }: FilterFormProps) {
  const { t } = useTranslation();
  return (
    <form onSubmit={submit}>
      <Stack gap="sm">
        <TextInput
          label={t("audit.search.household")}
          error={errors.household}
          value={draft.household}
          onChange={(e) => update("household", e.currentTarget.value)}
        />
        <TextInput
          label={t("audit.search.actor")}
          error={errors.actor}
          value={draft.actor}
          onChange={(e) => update("actor", e.currentTarget.value)}
        />
        <Group grow>
          <TextInput
            type="date"
            label={t("audit.search.from")}
            value={draft.from}
            onChange={(e) => update("from", e.currentTarget.value)}
          />
          <TextInput
            type="date"
            label={t("audit.search.to")}
            error={errors.to}
            value={draft.to}
            onChange={(e) => update("to", e.currentTarget.value)}
          />
        </Group>
        <Group>
          <Button type="submit">{t("audit.search.submit")}</Button>
        </Group>
      </Stack>
    </form>
  );
}

/** Render localized audit rows without exposing metadata beyond outcomes. */
function AuditTable({
  data,
  labels,
  locale,
}: {
  data: AuditPage;
  labels: Record<string, string>;
  locale: string;
}) {
  const { t } = useTranslation();
  return (
    <Table.ScrollContainer minWidth={800}>
      <Table striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            {(["when", "actor", "role", "action", "target", "outcome"] as const).map((key) => (
              <Table.Th key={key}>{t(`audit.search.${key}`)}</Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {data.results.map((event) => {
            const outcome = getOutcome(event.metadata);
            return (
              <Table.Tr key={event.id}>
                <Table.Td>
                  {new Intl.DateTimeFormat(locale, {
                    dateStyle: "medium",
                    timeStyle: "short",
                    timeZone: "America/Montreal",
                  }).format(new Date(event.created_at))}
                </Table.Td>
                <Table.Td>{event.actor}</Table.Td>
                <Table.Td>{labels[event.actor_role] ?? event.actor_role}</Table.Td>
                <Table.Td>{labels[event.action] ?? event.action}</Table.Td>
                <Table.Td>
                  {labels[event.target_type] ?? event.target_type}: {event.target_id}
                </Table.Td>
                <Table.Td>{outcome ? (labels[outcome] ?? outcome) : "—"}</Table.Td>
              </Table.Tr>
            );
          })}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

/** Build translated labels for the bounded audit enum values. */
function labelsFor(t: TFunction): Record<string, string> {
  return {
    admin: t("audit.search.roleAdmin"),
    intake_worker: t("audit.search.roleIntake"),
    store_staff: t("audit.search.roleStoreStaff"),
    store_manager: t("audit.search.roleStoreManager"),
    beneficiary: t("audit.search.roleBeneficiary"),
    view: t("audit.search.actionView"),
    decision: t("audit.search.actionDecision"),
    suspend: t("audit.search.actionSuspend"),
    reactivate: t("audit.search.actionReactivate"),
    approved: t("audit.search.outcomeApproved"),
    rejected: t("audit.search.outcomeRejected"),
    review_required: t("audit.search.outcomeReview"),
    household: t("audit.search.targetHousehold"),
  };
}

/** Own validated filters, pagination and the audit query. */
function useAuditSearch() {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<Filters>(emptyFilters);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [page, setPage] = useState(1);
  const [errors, setErrors] = useState<Partial<Record<keyof Filters, string>>>({});
  const query = useQuery({
    queryKey: ["audit", filters, page],
    queryFn: () => getAuditEvents(filters, page),
    gcTime: 0,
  });
  const update = (key: keyof Filters, value: string) =>
    setDraft((old) => ({ ...old, [key]: value }));
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const next: Partial<Record<keyof Filters, string>> = {};
    const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    for (const field of ["household", "actor"] as const)
      if (draft[field].trim() && !uuid.test(draft[field].trim()))
        next[field] = t("audit.search.invalidId");
    if (draft.from && draft.to && draft.from > draft.to) next.to = t("audit.search.invalidRange");
    setErrors(next);
    if (!Object.keys(next).length) {
      setPage(1);
      setFilters(draft);
    }
  };
  return { draft, errors, page, query, setPage, submit, update };
}

/** Render the current audit query state and page controls. */
function AuditContent({
  page,
  query,
  setPage,
}: {
  page: number;
  query: ReturnType<typeof useAuditSearch>["query"];
  setPage: Dispatch<SetStateAction<number>>;
}) {
  const { t, i18n } = useTranslation();
  if (query.isPending) return <LoadingState />;
  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />;
  if (!query.data?.results.length) return <EmptyState title={t("audit.search.empty")} />;
  return (
    <>
      <Text>{t("audit.search.count", { total: query.data.count })}</Text>
      <AuditTable
        data={query.data}
        labels={labelsFor(t)}
        locale={i18n.resolvedLanguage === "en" ? "en-CA" : "fr-CA"}
      />
      <Group>
        <Button
          variant="default"
          disabled={!query.data.previous}
          onClick={() => setPage((p) => p - 1)}
        >
          {t("audit.search.previous")}
        </Button>
        <Text>{t("audit.search.page", { page })}</Text>
        <Button variant="default" disabled={!query.data.next} onClick={() => setPage((p) => p + 1)}>
          {t("audit.search.next")}
        </Button>
      </Group>
    </>
  );
}

/** Keep audit query, filters and pagination in one page-level state owner. */
export function Audit() {
  const { t } = useTranslation();
  const search = useAuditSearch();
  return (
    <Stack gap="md">
      <Title order={1}>{t("app.staffNav.auditLog")}</Title>
      <Text c="dimmed">{t("audit.search.description")}</Text>
      <AuditFilterForm
        draft={search.draft}
        errors={search.errors}
        submit={search.submit}
        update={search.update}
      />
      <AuditContent page={search.page} query={search.query} setPage={search.setPage} />
    </Stack>
  );
}
