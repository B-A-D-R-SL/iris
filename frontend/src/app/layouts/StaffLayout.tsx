// AI contribution: 50% or more AI-generated
import { AppShell, Box, Burger, NavLink, Text } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconUserCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { Link, Outlet, useLocation } from "react-router";

import { useCurrentUser } from "../../shared/auth/currentUser";
import { SignOutButton } from "../../shared/auth/SignOutButton";
import { LanguageSwitch } from "../../shared/ui";
import { activeNavPath, navFor } from "../navigation";
import classes from "./layouts.module.css";
import { Wordmark } from "./Wordmark";

interface MenuProps {
  opened: boolean;
  onToggle: () => void;
}

/** Top bar: menu button below 992 px, the workspace name, language, sign-out and the user. */
function StaffHeader({ opened, onToggle }: MenuProps) {
  const { t } = useTranslation();
  const { data: user } = useCurrentUser();
  return (
    <div className={classes.staffHeader}>
      <Burger
        opened={opened}
        onClick={onToggle}
        hiddenFrom="md"
        size="sm"
        aria-label={t(opened ? "app.staffBar.closeMenu" : "app.staffBar.openMenu")}
      />
      <div className={classes.staffBrand}>
        <Wordmark subtitle={t("app.staffBar.workspace")} strong />
      </div>
      <LanguageSwitch />
      <SignOutButton />
      {user && (
        <Box className={classes.staffUser} visibleFrom="sm">
          <IconUserCircle size={24} stroke={2} aria-hidden />
          <span>{user.name}</span>
        </Box>
      )}
    </div>
  );
}

/** Side nav: the screens this user's role may open, the current one marked. */
function StaffSideNav({ onNavigate }: { onNavigate: () => void }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const { data: user } = useCurrentUser();
  const items = user ? navFor("staff", user.role) : [];
  const activePath = activeNavPath(items, pathname);
  return (
    <>
      <Text className={classes.sideNavHeading} id="staff-nav-heading">
        {t("app.staffNav.workspace")}
      </Text>
      <nav aria-labelledby="staff-nav-heading">
        {items.map(({ path, labelKey, icon: Icon }) => (
          <NavLink
            key={path}
            component={Link}
            to={path}
            label={t(labelKey)}
            leftSection={<Icon size={20} stroke={2} aria-hidden />}
            active={path === activePath}
            aria-current={path === activePath ? "page" : undefined}
            className={classes.sideNavLink}
            onClick={onNavigate}
          />
        ))}
      </nav>
      <Text className={classes.sideNavFooter}>{t("app.staffNav.accessNotice")}</Text>
    </>
  );
}

/**
 * B.A.D.R. staff screens (intake workers, admins): top bar + side nav from
 * 992 px (tablet landscape); on smaller screens the side nav opens from a menu button.
 */
export function StaffLayout() {
  const [opened, { toggle, close }] = useDisclosure(false);
  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 220, breakpoint: "md", collapsed: { mobile: !opened } }}
    >
      <AppShell.Header>
        <StaffHeader opened={opened} onToggle={toggle} />
      </AppShell.Header>
      <AppShell.Navbar className={classes.sideNav}>
        <StaffSideNav onNavigate={close} />
      </AppShell.Navbar>
      <AppShell.Main>
        <div className={classes.staffContent}>
          <Outlet />
        </div>
      </AppShell.Main>
    </AppShell>
  );
}
