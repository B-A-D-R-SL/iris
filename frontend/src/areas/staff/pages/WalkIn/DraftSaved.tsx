// AI contribution: 50% or more AI-generated
import { Button, Group, List, Stack, Text, Title } from "@mantine/core";
import { IconInfoCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import classes from "./WalkIn.module.css";
import { stillToComplete, type WalkInFormValues } from "./walkInForm";

interface DraftSavedProps {
  values: WalkInFormValues;
  onResume: () => void;
  /** The saved draft; its notices are recorded on their own page (US-18). */
  householdId?: string;
}

/** Figma W3.2a "Draft saved": what is still missing and how to resume. */
export function DraftSaved({ values, onResume, householdId }: DraftSavedProps) {
  const { t } = useTranslation();
  const name = `${values.firstName} ${values.lastName}`.trim();
  return (
    <Stack gap="lg" align="flex-start">
      <IconInfoCircle size={48} stroke={1.5} aria-hidden />
      <div>
        <Title order={1}>{t("staff.walkIn.draftSaved")}</Title>
        <Text c="gray.7">{t("staff.walkIn.draftSavedDescription", { name })}</Text>
      </div>
      <section className={classes.card} aria-labelledby="still-to-complete">
        <Title order={2} id="still-to-complete" className={classes.memberTitle} mb="xs">
          {t("staff.walkIn.stillToComplete")}
        </Title>
        <List c="gray.7">
          {stillToComplete(values).map((key) => (
            <List.Item key={key}>{t(key)}</List.Item>
          ))}
        </List>
      </section>
      <Group gap="sm">
        <Button onClick={onResume}>{t("staff.walkIn.resume")}</Button>
        {householdId && (
          <Button variant="outline" component={Link} to={`/staff/walk-in/${householdId}/notices`}>
            {t("staff.walkInNotices.open")}
          </Button>
        )}
        <Button variant="outline" component={Link} to="/staff/households">
          {t("staff.walkIn.backToHouseholds")}
        </Button>
      </Group>
    </Stack>
  );
}
