// AI contribution: 50% or more AI-generated
import { Button, Group, Stack, Table, Text, TextInput } from "@mantine/core";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { components } from "../../../shared/api/generated";
import type { Filters } from "./Audit";

type Event = components["schemas"]["PaginatedAuditEventList"]["results"][number];
const empty: Filters = { household: "", actor: "", from: "", to: "" };

export function AuditFilterForm({ onSubmit }: { onSubmit: (filters: Filters) => void }) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<Filters>(empty);
  const [errors, setErrors] = useState<Partial<Record<keyof Filters, string>>>({});
  const update = (key: keyof Filters, value: string) =>
    setDraft((old) => ({ ...old, [key]: value }));
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const next = validateFilters(draft, t);
    setErrors(next);
    if (!Object.keys(next).length) onSubmit(draft);
  };
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

function validateFilters(draft: Filters, t: (key: string) => string) {
  const errors: Partial<Record<keyof Filters, string>> = {};
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  for (const field of ["household", "actor"] as const) {
    if (draft[field].trim() && !uuid.test(draft[field].trim()))
      errors[field] = t("audit.search.invalidId");
  }
  if (draft.from && draft.to && draft.from > draft.to) errors.to = t("audit.search.invalidRange");
  return errors;
}

function getOutcome(metadata: unknown): string | undefined {
  if (
    typeof metadata === "object" &&
    metadata !== null &&
    "outcome" in metadata &&
    typeof metadata.outcome === "string"
  )
    return metadata.outcome;
}

export function AuditResultsTable({
  events,
  labels,
  locale,
}: {
  events: Event[];
  labels: Record<string, string>;
  locale: string;
}) {
  const { t } = useTranslation();
  return (
    <Table.ScrollContainer minWidth={800}>
      <Table striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            {["when", "actor", "role", "action", "target", "outcome"].map((key) => (
              <Table.Th key={key}>{t(`audit.search.${key}`)}</Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {events.map((event) => {
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

export function AuditPagination({
  page,
  previous,
  next,
  onPage,
}: {
  page: number;
  previous: boolean;
  next: boolean;
  onPage: (page: number) => void;
}) {
  const { t } = useTranslation();
  return (
    <Group>
      <Button variant="default" disabled={!previous} onClick={() => onPage(page - 1)}>
        {t("audit.search.previous")}
      </Button>
      <Text>{t("audit.search.page", { page })}</Text>
      <Button variant="default" disabled={!next} onClick={() => onPage(page + 1)}>
        {t("audit.search.next")}
      </Button>
    </Group>
  );
}
