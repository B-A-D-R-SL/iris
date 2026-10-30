// AI contribution: 50% or more AI-generated
import { Anchor, Button, Card, Stack, Text, Title } from "@mantine/core";
import { IconBuildingStore, IconHome } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { Link, Navigate } from "react-router";

import { homePathFor } from "../../app/navigation";
import { useCurrentUser } from "../../features/accounts/currentUser";

/** "/" — what Iris is, sign in, apply, become a partner (screens.md, SET-16). */
export function WelcomePage() {
  const { t } = useTranslation();
  const { data: user } = useCurrentUser();

  if (user) return <Navigate to={homePathFor(user.role)} replace />;

  return (
    <Stack gap="xl">
      <Stack gap="xs">
        <Title order={1}>{t("public.welcome.title")}</Title>
        <Text>{t("public.welcome.intro")}</Text>
      </Stack>

      <Button component={Link} to="/sign-in" fullWidth>
        {t("auth.common.signIn")}
      </Button>

      <Card withBorder radius="md" padding="md">
        <Stack gap="sm">
          <IconHome size={24} stroke={2} aria-hidden />
          <Title order={2}>{t("public.welcome.householdTitle")}</Title>
          <Text size="sm">{t("public.welcome.householdText")}</Text>
          <Button component={Link} to="/sign-up" variant="outline" fullWidth>
            {t("public.welcome.apply")}
          </Button>
        </Stack>
      </Card>

      <Card withBorder radius="md" padding="md">
        <Stack gap="sm">
          <IconBuildingStore size={24} stroke={2} aria-hidden />
          <Title order={2}>{t("public.welcome.partnerTitle")}</Title>
          <Text size="sm">{t("public.welcome.partnerText")}</Text>
          <Button component={Link} to="/partner/apply" variant="outline" fullWidth>
            {t("store.partnerApplication.becomePartner")}
          </Button>
        </Stack>
      </Card>

      <Anchor component={Link} to="/privacy" size="sm" ta="center">
        {t("privacy.common.privacyPolicy")}
      </Anchor>
    </Stack>
  );
}
