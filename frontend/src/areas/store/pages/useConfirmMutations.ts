// AI contribution: 50% or more AI-generated
import { useMutation } from "@tanstack/react-query";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";

import {
  confirmPickup,
  lookupPickup,
  PickupFailed,
  type Pickup,
} from "../../../features/reservations/pickupApi";
import { logger } from "../../../shared/logger";
import type { ConfirmStep } from "./confirmTypes";
import type { Language } from "./confirmFormat";

function asPickupFailed(error: unknown): PickupFailed {
  return error instanceof PickupFailed
    ? error
    : new PickupFailed(0, { code: "unavailable", message: "", fields: {} });
}

/** Lookup and confirm mutations shared by the Confirm step machine. */
export function useConfirmMutations(
  language: Language,
  setStep: Dispatch<SetStateAction<ConfirmStep>>,
  setNow: Dispatch<SetStateAction<Date>>,
  lookupLockRef: MutableRefObject<boolean>,
) {
  const lookup = useMutation({
    mutationFn: (code: string) => lookupPickup(code, language),
    onSuccess: (pickup) => {
      setNow(new Date());
      setStep({ kind: "review", pickup });
    },
    onError: (error, code) => {
      logger.error("pickup_lookup_failed");
      setStep({ kind: "scan", code, error: asPickupFailed(error) });
    },
    onSettled: () => {
      lookupLockRef.current = false;
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
      if (failed.code === "unavailable") return;
      setStep({ kind: "scan", code: pickup.pickup_code, error: failed });
    },
  });

  return { lookup, confirm, asPickupFailed };
}
