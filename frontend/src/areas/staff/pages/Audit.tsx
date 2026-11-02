// AI contribution: 50% or more AI-generated
import { Button, Group, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import type { components } from "../../../shared/api/generated";
import { EmptyState, ErrorState, LoadingState } from "../../../shared/ui";

type AuditPage = components["schemas"]["PaginatedAuditEventList"];

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

async function getAuditEvents(filters: Filters, page: number): Promise<AuditPage> {
  const params = new URLSearchParams({ page: String(page) });
  for (const [key, value] of Object.entries(filters)) {
    if (value.trim()) params.set(key, value.trim());
  }
  const response = await fetch(`/api/staff/audit/?${params}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`Audit search failed: ${response.status}`);
  return (await response.json()) as AuditPage;
}

export function Audit() {
  const { t, i18n } = useTranslation();
  const [draft, setDraft] = useState<Filters>(emptyFilters);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [page, setPage] = useState(1);
  const [errors, setErrors] = useState<Partial<Record<keyof Filters, string>>>({});
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["audit", filters, page],
    queryFn: () => getAuditEvents(filters, page),
    gcTime: 0,
  });
  const update = (key: keyof Filters, value: string) =>
    setDraft((previous) => ({ ...previous, [key]: value }));
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const nextErrors: Partial<Record<keyof Filters, string>> = {};
    const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    for (const field of ["household", "actor"] as const) {
      if (draft[field].trim() && !uuid.test(draft[field].trim())) {
        nextErrors[field] = t("audit.search.invalidId");
      }
    }
    if (draft.from && draft.to && draft.from > draft.to) {
      nextErrors.to = t("audit.search.invalidRange");
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    setPage(1);
    setFilters(draft);
  };
  const locale = i18n.resolvedLanguage === "en" ? "en-CA" : "fr-CA";
  const labels: Record<string, string> = {
    admin: t("audit.search.roleAdmin"),
    intake_worker: t("audit.search.roleIntake"),
    store_staff: t("audit.search.roleStoreStaff"),
    store_manager: t("audit.search.roleStoreManager"),
    beneficiary: t("audit.search.roleBeneficiary"),
    view: t("audit.search.actionView"),
    decision: t("audit.search.actionDecision"),
    approved: t("audit.search.outcomeApproved"),
    rejected: t("audit.search.outcomeRejected"),
    review_required: t("audit.search.outcomeReview"),
    household: t("audit.search.targetHousehold"),
  };

  return (
    <Stack gap="md">
      <Title order={1}>{t("app.staffNav.auditLog")}</Title>
      <Text c="dimmed">{t("audit.search.description")}</Text>
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
      {isPending ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState onRetry={() => void refetch()} />
      ) : !data || data.results.length === 0 ? (
        <EmptyState title={t("audit.search.empty")} />
      ) : (
        <>
          <Text>{t("audit.search.count", { total: data.count })}</Text>
          <Table.ScrollContainer minWidth={800}>
            <Table striped highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t("audit.search.when")}</Table.Th>
                  <Table.Th>{t("audit.search.actor")}</Table.Th>
                  <Table.Th>{t("audit.search.role")}</Table.Th>
                  <Table.Th>{t("audit.search.action")}</Table.Th>
                  <Table.Th>{t("audit.search.target")}</Table.Th>
                  <Table.Th>{t("audit.search.outcome")}</Table.Th>
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
          <Group>
            <Button
              variant="default"
              disabled={!data.previous}
              onClick={() => setPage((p) => p - 1)}
            >
              {t("audit.search.previous")}
            </Button>
            <Text>{t("audit.search.page", { page })}</Text>
            <Button variant="default" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>
              {t("audit.search.next")}
            </Button>
          </Group>
        </>
      )}
    </Stack>
  );
}
