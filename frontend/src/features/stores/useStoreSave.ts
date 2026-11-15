// AI contribution: 50% or more AI-generated
/**
 * Saving the store edit screen (US-14): PATCH only the changed fields, then
 * deactivate or reactivate with the reason when the status switch changed.
 * A PATCH that succeeded before a failed status change is not sent again.
 */
import type { UseFormReturnType } from "@mantine/form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { useNavigate } from "react-router";

import {
  deactivateStore,
  reactivateStore,
  StoreFailed,
  staffStoreKey,
  staffStoresKey,
  updateStore,
  type StaffStore,
} from "./adminApi";
import { changedFields, toFormValues, type StoreFormValues } from "./storeForm";

export type StatusChange = "deactivate" | "reactivate" | null;

/** What the list shows after saving (W7.2b, W7.4). */
export type StoreNotice =
  | { kind: "saved" | "reactivated"; name: string }
  | { kind: "deactivated"; name: string; listings: number; households: number };

/** Server field names match the form, except the schedule; the reason stays in the dialog. */
export function serverFieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof StoreFailed) || error.status !== 400) return {};
  const errors: Record<string, string> = {};
  for (const [field, messages] of Object.entries(error.fields)) {
    if (field === "reason" || !messages[0]) continue;
    errors[field === "opening_hours" ? "hours" : field] = messages[0];
  }
  return errors;
}

interface SaveOptions {
  store: StaffStore;
  form: UseFormReturnType<StoreFormValues>;
  statusChange: StatusChange;
  language: "fr" | "en";
  onError: (error: unknown) => void;
}

export function useStoreSave({ store, form, statusChange, language, onError }: SaveOptions) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const baseline = useRef<StoreFormValues>(toFormValues(store));

  return useMutation({
    mutationFn: async (reason: string | null): Promise<StoreNotice | null> => {
      const changes = changedFields(baseline.current, form.values);
      const changed = Object.keys(changes).length > 0;
      if (changed) baseline.current = toFormValues(await updateStore(store.id, changes, language));
      if (statusChange === "deactivate" && reason) {
        const result = await deactivateStore(store.id, reason, language);
        const households = store.households_to_notify;
        return {
          kind: "deactivated",
          name: store.name,
          listings: result.listings_cancelled,
          households,
        };
      }
      if (statusChange === "reactivate" && reason) {
        await reactivateStore(store.id, reason, language);
        return { kind: "reactivated", name: store.name };
      }
      return changed ? { kind: "saved", name: form.values.name.trim() } : null;
    },
    onSuccess: (notice) => {
      void queryClient.invalidateQueries({ queryKey: staffStoresKey });
      void queryClient.invalidateQueries({ queryKey: staffStoreKey(store.id) });
      void navigate("/staff/stores", { state: notice ? { notice } : null });
    },
    onError,
  });
}
