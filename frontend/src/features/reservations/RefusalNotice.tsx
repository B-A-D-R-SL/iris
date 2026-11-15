// AI contribution: 50% or more AI-generated
/**
 * The refusal notice at the top of the listing page (US-41, mockup H1 4a/4b).
 * It is brought into view when it appears, since the Reserve button that was
 * just tapped sits at the bottom of the page.
 */
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { Notice } from "../../shared/ui";
import { refusalNotice } from "./refusalMessage";
import classes from "./RefusalNotice.module.css";

export function RefusalNotice({ code }: { code: string }) {
  const { t } = useTranslation();
  const top = useRef<HTMLDivElement>(null);
  const notice = refusalNotice(code);

  useEffect(() => {
    // jsdom has no scrollIntoView, so call it only where it exists.
    top.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }, [code]);

  return (
    <div ref={top} className={classes.notice}>
      <Notice type={notice.type} title={notice.titleKey ? t(notice.titleKey) : undefined}>
        {t(notice.messageKey)}
      </Notice>
    </div>
  );
}
