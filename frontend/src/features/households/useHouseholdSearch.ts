// AI contribution: 50% or more AI-generated
import { useDebouncedValue } from "@mantine/hooks";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { searchHouseholds } from "./searchApi";

/** Distinct query keys and AbortSignal prevent older requests replacing newer results. */
export function useHouseholdSearch() {
  const { i18n } = useTranslation();
  const [input, setInput] = useState("");
  const [page, setPage] = useState(1);
  const term = input.trim();
  const [debounced] = useDebouncedValue(term, 300);
  const isTyping = term !== debounced;
  const language = i18n.resolvedLanguage === "en" ? "en" : "fr";
  const result = useQuery({
    queryKey: ["household-search", debounced, page, language],
    queryFn: ({ signal }) => searchHouseholds(debounced, page, language, signal),
    enabled: Boolean(term) && !isTyping,
    gcTime: 0,
    retry: false,
    refetchOnWindowFocus: false,
  });
  function changeInput(value: string) {
    setInput(value);
    setPage(1);
  }
  return { input, term, page, setPage, changeInput, isTyping, result };
}
