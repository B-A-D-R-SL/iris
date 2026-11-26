// AI contribution: 50% or more AI-generated
import { Button } from "@mantine/core";
import { IconWorld } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { useLanguageSwitch } from "../i18n/useLanguageSwitch";

/** Shows the other language ("English" while in French), as in the Figma app bars. */
export function LanguageSwitch() {
  const { t } = useTranslation();
  const { next, switchLanguage } = useLanguageSwitch();

  return (
    <Button
      variant="subtle"
      size="sm"
      leftSection={<IconWorld size={20} stroke={2} aria-hidden />}
      onClick={() => void switchLanguage()}
      lang={next}
    >
      {t("app.language.switchTo")}
    </Button>
  );
}
