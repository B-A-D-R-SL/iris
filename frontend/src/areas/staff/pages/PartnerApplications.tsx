// AI contribution: 50% or more AI-generated
import {
  Button,
  Drawer,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { csrfToken } from "../../../shared/api/csrf";
import type { components } from "../../../shared/api/generated";
import { logger } from "../../../shared/logger";
import { EmptyState, ErrorState, LoadingState, Notice } from "../../../shared/ui";

type Application = components["schemas"]["StaffPartnerApplication"];
type Page = components["schemas"]["PaginatedStaffPartnerApplicationList"];
type Decision = "approve" | "reject";
const endpoint = "/api/staff/partner-applications/";

class DecisionFailed extends Error {
  readonly status: number;

  constructor(status: number, message = "") {
    super(message);
    this.name = "DecisionFailed";
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Read public client-error messages; server failures use translated fallback text. */
async function decisionFailure(response: Response): Promise<DecisionFailed> {
  if (![400, 403, 404, 409].includes(response.status)) return new DecisionFailed(response.status);
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    logger.warning("partner_application_response_invalid");
    return new DecisionFailed(response.status);
  }
  if (
    !isRecord(data) ||
    typeof data.code !== "string" ||
    typeof data.message !== "string" ||
    !isRecord(data.fields)
  ) {
    logger.warning("partner_application_response_invalid");
    return new DecisionFailed(response.status);
  }
  const messages = Object.values(data.fields).flatMap((value) =>
    Array.isArray(value) && value.every((message) => typeof message === "string")
      ? value.filter((message: string) => message.trim())
      : [],
  );
  return new DecisionFailed(response.status, messages.join(" ") || data.message);
}

async function listApplications(status: string, page: number): Promise<Page> {
  const params = new URLSearchParams({ page: String(page) });
  if (status) params.set("status", status);
  const response = await fetch(`${endpoint}?${params}`, { credentials: "same-origin" });
  if (!response.ok) throw new Error("Unable to load applications");
  return response.json() as Promise<Page>;
}
async function decide(
  application: Application,
  decision: Decision,
  reason: string,
  language: string,
) {
  const token = csrfToken();
  // Django's locale cookie takes precedence over Accept-Language.
  document.cookie = `django_language=${language}; Path=/; SameSite=Lax`;
  const response = await fetch(`${endpoint}${encodeURIComponent(application.id)}/${decision}/`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "Accept-Language": language,
      ...(token ? { "X-CSRFToken": token } : {}),
    },
    body: JSON.stringify(decision === "reject" ? { reason: reason.trim() } : {}),
  });
  if (!response.ok) throw await decisionFailure(response);
  return response.json() as Promise<Application>;
}
export function PartnerApplications() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Application | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState(false);
  const [outcome, setOutcome] = useState<"success" | "error" | null>(null);
  const query = useQuery({
    queryKey: ["partner-applications", status, page],
    queryFn: () => listApplications(status, page),
    gcTime: 0,
  });
  const mutation = useMutation({
    mutationFn: ({ application, action }: { application: Application; action: Decision }) =>
      decide(application, action, reason, i18n.resolvedLanguage === "en" ? "en" : "fr"),
    onSuccess: () => {
      setDecision(null);
      setSelected(null);
      setPage(1);
      setReason("");
      setOutcome("success");
      void queryClient.invalidateQueries({ queryKey: ["partner-applications"] });
    },
    onError: (error) => {
      if (!(error instanceof DecisionFailed) || error.status >= 500) {
        logger.error("partner_application_request_failed");
      }
      setDecision(null);
      setSelected(null);
      setPage(1);
      setOutcome("error");
      void queryClient.invalidateQueries({ queryKey: ["partner-applications"] });
    },
  });
  const key = "store.partnerReview";
  const failure = mutation.error instanceof DecisionFailed ? mutation.error : null;
  const errorMessage =
    failure?.message ||
    t(`${key}.${failure?.status === 409 ? "alreadyDecidedMessage" : "errorMessage"}`);
  const camel = (value: string) =>
    value.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
  const date = (value: string) =>
    new Intl.DateTimeFormat(i18n.resolvedLanguage === "en" ? "en-CA" : "fr-CA", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "America/Montreal",
    }).format(new Date(value));
  const closeDecision = () => {
    if (!mutation.isPending) {
      setDecision(null);
      setReasonError(false);
    }
  };
  return (
    <Stack gap="md">
      <Title order={1}>{t(`${key}.title`)}</Title>
      <Select
        label={t(`${key}.filter`)}
        value={status}
        allowDeselect={false}
        onChange={(value) => {
          setStatus(value ?? "");
          setPage(1);
        }}
        data={[
          { value: "", label: t(`${key}.all`) },
          ...(["submitted", "approved", "rejected"] as const).map((value) => ({
            value,
            label: t(`${key}.${value}`),
          })),
        ]}
      />
      {outcome && (
        <Notice type={outcome} title={t(`${key}.${outcome}`)}>
          {outcome === "error" ? errorMessage : t(`${key}.successMessage`)}
        </Notice>
      )}
      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} />
      ) : !query.data.results.length ? (
        <EmptyState title={t(`${key}.empty`)} />
      ) : (
        <>
          <Table.ScrollContainer minWidth={650}>
            <Table striped highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t(`${key}.business`)}</Table.Th>
                  <Table.Th>{t(`${key}.contact`)}</Table.Th>
                  <Table.Th>{t(`${key}.status`)}</Table.Th>
                  <Table.Th>{t(`${key}.received`)}</Table.Th>
                  <Table.Th>{t(`${key}.actions`)}</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {query.data.results.map((item) => (
                  <Table.Tr key={item.id}>
                    <Table.Td>{item.business_name}</Table.Td>
                    <Table.Td>{item.contact_email}</Table.Td>
                    <Table.Td>{t(`${key}.${item.status}`)}</Table.Td>
                    <Table.Td>{date(item.created_at)}</Table.Td>
                    <Table.Td>
                      <Button
                        variant="subtle"
                        aria-label={t(`${key}.viewName`, { name: item.business_name })}
                        onClick={() => {
                          setSelected(item);
                          setOutcome(null);
                        }}
                      >
                        {t(`${key}.view`)}
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          <Group>
            <Button
              variant="default"
              disabled={!query.data.previous}
              onClick={() => setPage((p) => p - 1)}
            >
              {t(`${key}.previous`)}
            </Button>
            <Text>{t(`${key}.page`, { page })}</Text>
            <Button
              variant="default"
              disabled={!query.data.next}
              onClick={() => setPage((p) => p + 1)}
            >
              {t(`${key}.next`)}
            </Button>
          </Group>
        </>
      )}
      <Drawer
        opened={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.business_name}
        position="right"
        size="lg"
      >
        {selected && (
          <Stack>
            {(
              [
                ["status", t(`${key}.${selected.status}`)],
                ["received", date(selected.created_at)],
                [
                  "businessType",
                  t(`store.partnerApplication.businessTypes.${camel(selected.business_type)}`),
                ],
                ["neq", selected.neq],
                ["website", selected.website],
                [
                  "address",
                  [
                    selected.street_number,
                    selected.street_name,
                    selected.unit,
                    selected.city,
                    selected.postal_code,
                  ]
                    .filter(Boolean)
                    .join(", "),
                ],
                ["contact", `${selected.contact_first_name} ${selected.contact_last_name}`],
                ["contactRole", selected.contact_role],
                ["email", selected.contact_email],
                ["phone", selected.contact_phone],
                [
                  "categories",
                  selected.goods_categories
                    .map((code) => t(`listing.categories.${camel(code)}`, { defaultValue: code }))
                    .join(", "),
                ],
                [
                  "frequency",
                  t(`store.partnerApplication.donationFrequency.${selected.expected_frequency}`),
                ],
                ["hours", selected.opening_hours],
                ["message", selected.message],
                [
                  "language",
                  t(`${key}.${selected.language === "en" ? "languageEn" : "languageFr"}`),
                ],
                ["reason", selected.decision_reason],
                ["decided", selected.decided_at ? date(selected.decided_at) : null],
              ] as [string, string | null][]
            ).map(([label, value]) => (
              <div key={label}>
                <Text fw={600}>{t(`${key}.${label}`)}</Text>
                <Text style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                  {value || "—"}
                </Text>
              </div>
            ))}
            {selected.status === "submitted" && (
              <Group>
                <Button
                  onClick={() => {
                    setReason("");
                    setReasonError(false);
                    setDecision("approve");
                  }}
                >
                  {t(`${key}.approve`)}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setReason("");
                    setReasonError(false);
                    setDecision("reject");
                  }}
                >
                  {t(`${key}.reject`)}
                </Button>
              </Group>
            )}
          </Stack>
        )}
      </Drawer>
      <Modal
        opened={!!decision && !!selected}
        onClose={closeDecision}
        title={decision ? t(`${key}.${decision}Title`) : ""}
        closeOnClickOutside={!mutation.isPending}
        closeOnEscape={!mutation.isPending}
      >
        <Stack>
          <Text>{t(`${key}.confirm`, { name: selected?.business_name })}</Text>
          {decision === "reject" && (
            <Textarea
              label={t(`${key}.reason`)}
              required
              maxLength={500}
              value={reason}
              error={reasonError ? t(`${key}.reasonRequired`) : undefined}
              onChange={(e) => {
                setReason(e.currentTarget.value);
                setReasonError(false);
              }}
            />
          )}
          <Group justify="flex-end">
            <Button variant="default" disabled={mutation.isPending} onClick={closeDecision}>
              {t(`${key}.cancel`)}
            </Button>
            <Button
              loading={mutation.isPending}
              onClick={() => {
                if (!selected || !decision) return;
                if (decision === "reject" && !reason.trim()) {
                  setReasonError(true);
                  return;
                }
                mutation.mutate({ application: selected, action: decision });
              }}
            >
              {decision && t(`${key}.${decision}`)}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
