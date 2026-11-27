// AI contribution: 50% or more AI-generated
import { useRef, useState } from "react";

import {
  PasswordResetError,
  type PasswordResetErrorCode,
} from "../../../features/accounts/passwordReset";
import { logger } from "../../../shared/logger";

export type ResetFailure = { code: PasswordResetErrorCode | "checkForm" };

export function useResetSubmission() {
  const [pending, setPending] = useState(false);
  const [complete, setComplete] = useState(false);
  const [failure, setFailure] = useState<ResetFailure | null>(null);
  const submitting = useRef(false);

  async function run(action: () => Promise<void>) {
    if (submitting.current) return;
    submitting.current = true;
    setPending(true);
    setFailure(null);
    try {
      await action();
      setComplete(true);
    } catch (error) {
      if (!(error instanceof PasswordResetError)) logger.error("password_reset_request_failed");
      setFailure({ code: error instanceof PasswordResetError ? error.code : "unavailable" });
    } finally {
      submitting.current = false;
      setPending(false);
    }
  }

  return {
    pending,
    complete,
    failure,
    run,
    failValidation: () => setFailure({ code: "checkForm" }),
  };
}
