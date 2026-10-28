// AI contribution: 50% or more AI-generated
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router";

import { activeNavPath, type NavItem } from "../navigation";
import classes from "./layouts.module.css";

/** Phone tab bar of the household and store areas (Figma "Bottom nav", 64 px). */
export function BottomNav({ items }: { items: readonly NavItem[] }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const activePath = activeNavPath(items, pathname);

  return (
    <nav aria-label={t("app.mainNav.label")} className={classes.bottomNav}>
      {items.map(({ path, labelKey, icon: Icon }) => {
        const active = path === activePath;
        return (
          <Link
            key={path}
            to={path}
            className={classes.tab}
            data-active={active || undefined}
            aria-current={active ? "page" : undefined}
          >
            <span className={classes.pill}>
              <Icon size={22} stroke={2} aria-hidden />
            </span>
            <span className={classes.tabLabel}>{t(labelKey)}</span>
          </Link>
        );
      })}
    </nav>
  );
}
