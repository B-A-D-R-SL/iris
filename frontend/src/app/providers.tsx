// AI contribution: 50% or more AI-generated
import { MantineProvider } from "@mantine/core";
import { DatesProvider } from "@mantine/dates";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import "../shared/i18n/dates";
import { AppErrorBoundary } from "./AppErrorBoundary";
import { cssVariablesResolver, theme } from "./theme";

const defaultQueryClient = new QueryClient();

/** Date pickers follow the interface language; Quebec calendars start on Sunday. */
function LocalizedDates({ children }: { children: ReactNode }) {
  const { i18n } = useTranslation();
  return (
    <DatesProvider settings={{ locale: i18n.resolvedLanguage ?? "fr", firstDayOfWeek: 0 }}>
      {children}
    </DatesProvider>
  );
}

interface AppProvidersProps {
  children: ReactNode;
  /** Tests pass their own client (no retries, no shared cache). */
  queryClient?: QueryClient;
  /** "test" turns off Mantine transitions and portals. */
  env?: "default" | "test";
}

/** Everything around the routes; the router itself is added by main.tsx or the tests. */
export function AppProviders({
  children,
  queryClient = defaultQueryClient,
  env = "default",
}: AppProvidersProps) {
  return (
    <MantineProvider
      theme={theme}
      cssVariablesResolver={cssVariablesResolver}
      defaultColorScheme="light"
      env={env}
    >
      <LocalizedDates>
        <QueryClientProvider client={queryClient}>
          <AppErrorBoundary>{children}</AppErrorBoundary>
        </QueryClientProvider>
      </LocalizedDates>
    </MantineProvider>
  );
}
