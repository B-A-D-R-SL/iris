// AI contribution: 50% or more AI-generated
import { Button, Group, Stack, Table, Text, TextInput } from "@mantine/core";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { components } from "../../../shared/api/generated";
import { emptyFilters, useAuditFormatter, type Filters } from "./auditHelpers";

type Event = components["schemas"]["PaginatedAuditEventList"]["results"][number];

export function AuditFilterForm({ onSubmit }: { onSubmit: (filters: Filters) => void }) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<Filters>(emptyFilters);
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
  const formatter = useAuditFormatter(locale);
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
                <Table.Td>{formatter.format(new Date(event.created_at))}</Table.Td>
                <Table.Td>{event.actor ?? labels.system}</Table.Td>
                <Table.Td>{labels[event.actor_role] ?? event.actor_role}</Table.Td>
                <Table.Td>{labels[event.action] ?? event.action}</Table.Td>
                <Table.Td>
                  {labels[event.target_type] ?? event.target_type}: {event.target_id}
                  {event.action === "rule_published" && <RuleDetails metadata={event.metadata} />}
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

function RuleDetails({ metadata }: { metadata: unknown }) {
  const { t } = useTranslation();
  if (
    typeof metadata !== "object" ||
    metadata === null ||
    !("rule_type" in metadata) ||
    !("version" in metadata) ||
    typeof metadata.rule_type !== "string" ||
    typeof metadata.version !== "number" ||
    !Number.isInteger(metadata.version) ||
    metadata.version < 1
  )
    return null;
  const ruleKey = metadata.rule_type.replace(/_([a-z])/g, (_, letter: string) =>
    letter.toUpperCase(),
  );
  const key = `audit.ruleTypes.${ruleKey}`;
  return (
    <>
      {" "}
      ({t(key, { defaultValue: metadata.rule_type })},{" "}
      {t("audit.search.ruleVersion", { version: metadata.version })})
    </>
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
