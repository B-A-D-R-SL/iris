// AI contribution: 50% or more AI-generated
import { Stack, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "../../../shared/api/generated";
import { EmptyState, ErrorState, LoadingState } from "../../../shared/ui";
import { AuditFilterForm, AuditPagination, AuditResultsTable } from "./AuditComponents";
import { emptyFilters, useAuditLabels, type Filters } from "./auditHelpers";

type AuditPage = components["schemas"]["PaginatedAuditEventList"];

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

/** Keep audit query, filters and pagination in one page-level state owner. */
export function Audit() {
  const { t, i18n } = useTranslation();
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [page, setPage] = useState(1);
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["audit", filters, page],
    queryFn: () => getAuditEvents(filters, page),
    gcTime: 0,
  });
  const locale = i18n.resolvedLanguage === "en" ? "en-CA" : "fr-CA";
  const labels = useAuditLabels();

  return (
    <Stack gap="md">
      <Title order={1}>{t("app.staffNav.auditLog")}</Title>
      <Text c="dimmed">{t("audit.search.description")}</Text>
      <AuditFilterForm
        onSubmit={(next) => {
          setPage(1);
          setFilters(next);
        }}
      />
      {isPending ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState onRetry={() => void refetch()} />
      ) : !data || data.results.length === 0 ? (
        <EmptyState title={t("audit.search.empty")} />
      ) : (
        <>
          <Text>{t("audit.search.count", { total: data.count })}</Text>
          <AuditResultsTable events={data.results} labels={labels} locale={locale} />
          <AuditPagination
            page={page}
            previous={!!data.previous}
            next={!!data.next}
            onPage={setPage}
          />
        </>
      )}
    </Stack>
  );
}
