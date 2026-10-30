// AI contribution: 50% or more AI-generated
import { Button, Container } from "@mantine/core";
import { Component, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { logger } from "../shared/logger";
import { ErrorState } from "../shared/ui";

function CrashScreen() {
  const { t } = useTranslation();
  return (
    <Container size={560} py="xl">
      <ErrorState
        title={t("app.crash.title")}
        description={t("app.crash.description")}
        action={<Button onClick={() => window.location.reload()}>{t("app.crash.reload")}</Button>}
      />
    </Container>
  );
}

/** Last resort when a screen crashes: a plain message instead of a blank page. */
export class AppErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch() {
    // No error details: they can contain personal data (SEC-09).
    logger.error("app_render_failed");
  }

  render() {
    return this.state.failed ? <CrashScreen /> : this.props.children;
  }
}
