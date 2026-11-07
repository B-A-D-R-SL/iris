// AI contribution: 50% or more AI-generated
import { Badge, Button, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import {
  householdStatusLabels,
  type HouseholdSearchPage,
  type HouseholdSearchResult,
} from "../../../features/households/searchApi";
import classes from "./Search.module.css";

function HouseholdContact({ file }: { file: HouseholdSearchResult }) {
  const { t } = useTranslation();
  const street = [file.street_number, file.street_name].filter(Boolean).join(" ");
  const unit = file.unit ? t("household.search.unit", { unit: file.unit }) : "";
  const address = [street, unit, file.city, file.postal_code].filter(Boolean).join(", ");
  return (
    <dl className={classes.details}>
      <div>
        <dt>{t("household.search.email")}</dt>
        <dd>{file.email || t("household.search.notProvided")}</dd>
      </div>
      <div>
        <dt>{t("household.search.phone")}</dt>
        <dd>{file.phone || t("household.search.notProvided")}</dd>
      </div>
      <div className={classes.address}>
        <dt>{t("household.search.address")}</dt>
        <dd>{address || t("household.search.notProvided")}</dd>
      </div>
    </dl>
  );
}

function HouseholdCard({ file }: { file: HouseholdSearchResult }) {
  const { t } = useTranslation();
  const name = [file.first_name, file.last_name].filter(Boolean).join(" ");
  return (
    <Paper component="li" withBorder p="md">
      <Stack gap="sm">
        <Group justify="space-between" align="flex-start">
          <div className={classes.identity}>
            <Title order={2} size="h3">
              {name || t("household.search.unnamed")}
            </Title>
            <Text size="sm" c="dimmed">
              {file.member_number || t("household.search.noMemberNumber")}
            </Text>
          </div>
          <Badge variant="light">{t(householdStatusLabels[file.status])}</Badge>
        </Group>
        <HouseholdContact file={file} />
        {file.channel === "walk_in" && file.status === "draft" && (
          <Group>
            <Button component={Link} to={`/staff/walk-in/${file.id}`} variant="outline">
              {t("household.search.resume")}
            </Button>
          </Group>
        )}
      </Stack>
    </Paper>
  );
}

interface ResultsProps {
  data: HouseholdSearchPage;
  page: number;
  onPage: (page: number) => void;
}

export function SearchResults({ data, page, onPage }: ResultsProps) {
  const { t } = useTranslation();
  return (
    <Stack gap="md">
      <Text role="status">
        {t(data.count === 1 ? "household.search.countOne" : "household.search.countOther", {
          count: data.count,
        })}
      </Text>
      <Stack component="ul" gap="sm" className={classes.results}>
        {data.results.map((file) => (
          <HouseholdCard key={file.id} file={file} />
        ))}
      </Stack>
      <Group component="nav" aria-label={t("household.search.pagination")} justify="space-between">
        <Button variant="outline" disabled={!data.previous} onClick={() => onPage(page - 1)}>
          {t("household.search.previous")}
        </Button>
        <Text size="sm">{t("household.search.page", { page })}</Text>
        <Button variant="outline" disabled={!data.next} onClick={() => onPage(page + 1)}>
          {t("household.search.next")}
        </Button>
      </Group>
    </Stack>
  );
}
