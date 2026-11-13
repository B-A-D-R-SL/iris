// AI contribution: 50% or more AI-generated
import { useRef, useState } from "react";

import type { Pickup } from "../../../features/reservations/pickupApi";
import { draftCode } from "./confirmCode";
import type { ConfirmStep } from "./confirmTypes";
import type { Language } from "./confirmFormat";
import { useConfirmMutations } from "./useConfirmMutations";
import { useConfirmScanActions } from "./useConfirmScanActions";
import { usePickupClock } from "./usePickupClock";

export type { ConfirmStep } from "./confirmTypes";

/** Lookup / confirm mutations and scan→review→done step state for Confirm. */
export function useConfirmPickup(language: Language) {
  const [step, setStep] = useState<ConfirmStep>({ kind: "scan", code: "", error: null });
  const [now, setNow] = usePickupClock();
  const lookupLockRef = useRef(false);
  const scannedCodes = useRef(new Set<string>());
  const { lookup, confirm, asPickupFailed } = useConfirmMutations(
    language,
    setStep,
    setNow,
    lookupLockRef,
  );
  const { requestLookup, onDetected, resetScan } = useConfirmScanActions({
    lookup,
    confirm,
    setStep,
    lookupLockRef,
    scannedCodes,
  });

  const setScanCode = (value: string) => {
    if (step.kind !== "scan") return;
    setStep({ kind: "scan", code: draftCode(value), error: null });
  };

  return {
    step,
    now,
    busy: lookup.isPending || confirm.isPending,
    confirmError: confirm.error === null ? null : asPickupFailed(confirm.error),
    requestLookup,
    onDetected,
    resetScan,
    setScanCode,
    confirmPickup: (pickup: Pickup) => confirm.mutate(pickup),
  };
}

export type ConfirmFlowState = ReturnType<typeof useConfirmPickup>;
