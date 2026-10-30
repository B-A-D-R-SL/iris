// AI contribution: 50% or more AI-generated
import { ActionIcon, Menu, Title } from "@mantine/core";
import { IconArrowLeft, IconUserCircle, IconWorld } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { useCurrentUser } from "../../features/accounts/currentUser";
import { SignOutButton } from "../../shared/auth/SignOutButton";
import { logger } from "../../shared/logger";
import classes from "./layouts.module.css";

export interface AppBarProps {
  /** The screen title, for example "Publier une offre". */
  title: string;
  /** Sub-screens get a back arrow to this path (Figma app bar "Back"). */
  backTo?: string;
  /** Replaces the account menu on the right. */
  action?: ReactNode;
}

/** Top bar of household and store screens (Figma "App bar", 56 px). Each screen renders its own. */
export function AppBar({ title, backTo, action }: AppBarProps) {
  const { t } = useTranslation();
  return (
    <header className={classes.appBar} data-back={backTo ? true : undefined}>
      {backTo && (
        <ActionIcon
          component={Link}
          to={backTo}
          variant="subtle"
          size={48}
          aria-label={t("app.appBar.back")}
        >
          <IconArrowLeft size={24} stroke={2} aria-hidden />
        </ActionIcon>
      )}
      <Title order={1} className={classes.appBarTitle}>
        {title}
      </Title>
      {action ?? <AccountMenu />}
    </header>
  );
}

function AccountMenu() {
  const { t, i18n } = useTranslation();
  const { data: user } = useCurrentUser();
  const next = i18n.resolvedLanguage === "en" ? "fr" : "en";

  return (
    <Menu position="bottom-end" width={220} closeOnItemClick={false}>
      <Menu.Target>
        <ActionIcon variant="subtle" size={48} aria-label={t("app.appBar.account")}>
          <IconUserCircle size={24} stroke={2} aria-hidden />
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        {user && <Menu.Label>{user.name}</Menu.Label>}
        <Menu.Item
          leftSection={<IconWorld size={18} stroke={2} aria-hidden />}
          lang={next}
          onClick={() => void i18n.changeLanguage(next).then(() => logger.info("language_changed"))}
        >
          {t("app.language.switchTo")}
        </Menu.Item>
        <SignOutButton menu />
      </Menu.Dropdown>
    </Menu>
  );
}
