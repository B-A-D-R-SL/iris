// AI contribution: 50% or more AI-generated
import { ActionIcon, Button, Group, Stack, Text, TextInput, Title } from "@mantine/core";
import { IconSearch, IconX } from "@tabler/icons-react";
import { useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { HouseholdSearchError } from "../../../features/households/searchApi";
import { useHouseholdSearch } from "../../../features/households/useHouseholdSearch";
import { EmptyState, ErrorState, LoadingState } from "../../../shared/ui";
import { SearchResults } from "./SearchResults";

type SearchState = ReturnType<typeof useHouseholdSearch>;

function ClearSearch({ onClear }: { onClear: () => void }) {
  const { t } = useTranslation();
  return (
    <ActionIcon
      type="button"
      size="xl"
      variant="subtle"
      aria-label={t("household.search.clear")}
      onClick={onClear}
    >
      <IconX size={18} aria-hidden />
    </ActionIcon>
  );
}

function SearchControls({ state }: { state: SearchState }) {
  const { t } = useTranslation();
  const input = useRef<HTMLInputElement>(null);
  return (
    <form role="search" onSubmit={(event) => event.preventDefault()}>
      <TextInput
        type="search"
        ref={input}
        label={t("household.search.label")}
        description={t("household.search.description")}
        value={state.input}
        onChange={(event) => state.changeInput(event.currentTarget.value)}
        maxLength={254}
        autoComplete="off"
        spellCheck={false}
        rightSectionWidth={48}
        leftSection={<IconSearch size={20} aria-hidden />}
        rightSection={
          state.input ? (
            <ClearSearch
              onClear={() => {
                state.changeInput("");
                input.current?.focus();
              }}
            />
          ) : null
        }
      />
    </form>
  );
}

function SearchContent({ state }: { state: SearchState }) {
  const { t } = useTranslation();
  const { result } = state;
  if (!state.term) return <EmptyState title={t("household.search.start")} />;
  if (state.isTyping || result.isPending) return <LoadingState />;
  if (result.isError) {
    if (result.error instanceof HouseholdSearchError && [401, 403].includes(result.error.status)) {
      return (
        <ErrorState
          title={t("household.search.denied")}
          description={t("household.search.deniedDescription")}
          action={
            <Button component={Link} to="/sign-in">
              {t("household.search.signIn")}
            </Button>
          }
        />
      );
    }
    return <ErrorState onRetry={() => void result.refetch()} />;
  }
  if (!result.data?.results.length) {
    return (
      <EmptyState
        title={t("household.search.empty")}
        description={t("household.search.emptyDescription")}
      />
    );
  }
  return <SearchResults data={result.data} page={state.page} onPage={state.setPage} />;
}

export function Search() {
  const { t } = useTranslation();
  const state = useHouseholdSearch();
  return (
    <Stack gap="lg">
      <Group justify="space-between" align="center">
        <Title order={1}>{t("app.staffNav.households")}</Title>
        <Button component={Link} to="/staff/walk-in" variant="outline">
          {t("household.search.newRegistration")}
        </Button>
      </Group>
      <SearchControls state={state} />
      <Text size="sm" c="dimmed">
        {t("household.search.staffOnly")}
      </Text>
      <section
        aria-label={t("household.search.results")}
        aria-live="polite"
        aria-busy={Boolean(state.term) && (state.isTyping || state.result.isFetching)}
      >
        <SearchContent state={state} />
      </section>
    </Stack>
  );
}
