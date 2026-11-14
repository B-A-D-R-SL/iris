// AI contribution: 50% or more AI-generated
import { useCallback, type Dispatch, type MutableRefObject, type SetStateAction } from "react";

import type { Pickup } from "../../../features/reservations/pickupApi";
import { codeFromScan, draftCode, isCompleteCode } from "./confirmCode";
import type { ConfirmStep } from "./confirmTypes";

type MutateLookup = { mutate: (code: string) => void; reset: () => void; isPending: boolean };
type MutateConfirm = { mutate: (pickup: Pickup) => void; reset: () => void; isPending: boolean };

/** Typed/scan lookup triggers and reset for the Confirm step machine. */
export function useConfirmScanActions({
  lookup,
  confirm,
  setStep,
  lookupLockRef,
  scannedCodes,
}: {
  lookup: MutateLookup;
  confirm: MutateConfirm;
  setStep: Dispatch<SetStateAction<ConfirmStep>>;
  lookupLockRef: MutableRefObject<boolean>;
  scannedCodes: MutableRefObject<Set<string>>;
}) {
  const requestLookup = useCallback(
    (raw: string) => {
      const code = draftCode(raw);
      if (!isCompleteCode(code) || lookupLockRef.current || confirm.isPending) return;
      lookupLockRef.current = true;
      confirm.reset();
      setStep({ kind: "scan", code, error: null });
      lookup.mutate(code);
    },
    [confirm, lookup, lookupLockRef, setStep],
  );

  const onDetected = useCallback(
    (text: string) => {
      const code = codeFromScan(text);
      if (!code || scannedCodes.current.has(code) || lookupLockRef.current || confirm.isPending) {
        return;
      }
      scannedCodes.current.add(code);
      requestLookup(code);
    },
    [confirm.isPending, lookupLockRef, requestLookup, scannedCodes],
  );

  const resetScan = () => {
    lookupLockRef.current = false;
    scannedCodes.current.clear();
    lookup.reset();
    confirm.reset();
    setStep({ kind: "scan", code: "", error: null });
  };

  return { requestLookup, onDetected, resetScan };
}
