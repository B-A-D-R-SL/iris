// AI contribution: 50% or more AI-generated
import { useMutation } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import {
  confirmPickup,
  lookupPickup,
  PickupFailed,
  type Pickup,
} from "../../../features/reservations/pickupApi";
import { logger } from "../../../shared/logger";
import { codeFromScan, draftCode, isCompleteCode } from "./confirmCode";
import type { Language } from "./confirmFormat";

export type ConfirmStep =
  | { kind: "scan"; code: string; error: PickupFailed | null }
  | { kind: "review"; pickup: Pickup }
  | { kind: "done"; pickup: Pickup };

function asPickupFailed(error: unknown): PickupFailed {
  return error instanceof PickupFailed
    ? error
    : new PickupFailed(0, { code: "unavailable", message: "", fields: {} });
}

/**
 * Lookup / confirm mutations and scan→review→done step state for Confirm.
 * Size exception: the mutations share one lookup lock and step machine, so the
 * refusal and retry paths stay consistent in a single hook.
 */
export function useConfirmPickup(language: Language) {
  const [step, setStep] = useState<ConfirmStep>({ kind: "scan", code: "", error: null });
  const [now, setNow] = useState(() => new Date());
  const lookupLock = useRef(false);

  const lookup = useMutation({
    mutationFn: (code: string) => lookupPickup(code, language),
    onSuccess: (pickup) => {
      setNow(new Date());
      setStep({ kind: "review", pickup });
    },
    onError: (error, code) => {
      const failed = asPickupFailed(error);
      logger.error("pickup_lookup_failed");
      setStep({ kind: "scan", code, error: failed });
    },
    onSettled: () => {
      lookupLock.current = false;
    },
  });

  const confirm = useMutation({
    mutationFn: (pickup: Pickup) => confirmPickup(pickup.id, language),
    onSuccess: (pickup) => {
      logger.info("pickup_confirmed");
      setStep({ kind: "done", pickup });
    },
    onError: (error, pickup) => {
      const failed = asPickupFailed(error);
      logger.error("pickup_confirm_failed");
      // Transient network/server failures stay on review so staff can retry.
      if (failed.code === "unavailable") return;
      setStep({ kind: "scan", code: pickup.pickup_code, error: failed });
    },
  });

  const requestLookup = useCallback(
    (raw: string) => {
      const code = draftCode(raw);
      if (!isCompleteCode(code) || lookupLock.current || confirm.isPending) return;
      lookupLock.current = true;
      setStep({ kind: "scan", code, error: null });
      lookup.mutate(code);
    },
    [confirm.isPending, lookup],
  );

  const onDetected = useCallback(
    (text: string) => {
      const code = codeFromScan(text);
      if (code) requestLookup(code);
    },
    [requestLookup],
  );

  const resetScan = () => {
    lookupLock.current = false;
    lookup.reset();
    confirm.reset();
    setStep({ kind: "scan", code: "", error: null });
  };

  const setScanCode = (value: string) => {
    if (step.kind !== "scan") return;
    setStep({ kind: "scan", code: draftCode(value), error: step.error });
  };

  return {
    step,
    now,
    busy: lookup.isPending || confirm.isPending,
    confirmError: confirm.error instanceof PickupFailed ? confirm.error : null,
    requestLookup,
    onDetected,
    resetScan,
    setScanCode,
    confirmPickup: (pickup: Pickup) => confirm.mutate(pickup),
  };
}
