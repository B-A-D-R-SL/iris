// AI contribution: 50% or more AI-generated
import { AppShell } from "@mantine/core";
import { Outlet } from "react-router";

import { useCurrentUser } from "../../features/accounts/currentUser";
import { navFor } from "../navigation";
import { BottomNav } from "./BottomNav";
import classes from "./layouts.module.css";

/**
 * Household and store areas: phone-first screens with a bottom tab bar.
 * Each screen renders its own <AppBar> because titles and back arrows differ.
 */
export function MobileAreaLayout({ area }: { area: "household" | "store" }) {
  const { data: user } = useCurrentUser();
  const items = user ? navFor(area, user.role) : [];

  return (
    <AppShell footer={{ height: 64 }}>
      <AppShell.Main>
        <div className={classes.areaContent}>
          <Outlet />
        </div>
      </AppShell.Main>
      <AppShell.Footer>
        <BottomNav items={items} />
      </AppShell.Footer>
    </AppShell>
  );
}
