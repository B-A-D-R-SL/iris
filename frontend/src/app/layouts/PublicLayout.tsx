// AI contribution: 50% or more AI-generated
import { AppShell, Container } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { Link, Outlet } from "react-router";

import { LanguageSwitch } from "../../shared/ui";
import classes from "./layouts.module.css";
import { Wordmark } from "./Wordmark";

/** Pages without sign-in: welcome, sign-in, become a partner (Figma app bar "Public"). */
export function PublicLayout() {
  const { t } = useTranslation();
  return (
    <AppShell header={{ height: 56 }}>
      <AppShell.Header>
        <div className={classes.publicHeader}>
          <Link to="/" className={classes.homeLink} aria-label={t("app.brand.home")}>
            <Wordmark subtitle={t("app.brand.byBadr")} />
          </Link>
          <LanguageSwitch />
        </div>
      </AppShell.Header>
      <AppShell.Main>
        <Container size={560} px="md" py="lg">
          <Outlet />
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
