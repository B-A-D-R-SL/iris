// AI contribution: 50% or more AI-generated
import { Button } from "@mantine/core";
import { IconWorld } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { logger } from "../logger";

/** Shows the other language ("English" while in French), as in the Figma app bars. */
export function LanguageSwitch() {
  const { t, i18n } = useTranslation();
  const next = i18n.resolvedLanguage === "en" ? "fr" : "en";

  const switchLanguage = () => {
    void i18n.changeLanguage(next).then(() => logger.info("language_changed"));
  };

  return (
    <Button
      variant="subtle"
      size="sm"
      leftSection={<IconWorld size={20} stroke={2} aria-hidden />}
      onClick={switchLanguage}
      lang={next}
    >
      {t("app.language.switchTo")}
    </Button>
  );
}
