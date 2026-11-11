// AI contribution: 50% or more AI-generated
/** Structured, privacy-safe frontend events. No arbitrary user data is accepted. */

type FrontendEvent =
  | "unknown_status"
  | "language_changed"
  | "backend_health_unavailable"
  | "app_render_failed"
  | "auth_tab_sync_unavailable"
  | "sign_in_failed_unexpectedly"
  | "sign_out_failed"
  | "invitation_accept_failed_unexpectedly"
  | "invitation_response_invalid"
  | "invitation_request_failed"
  | "household_status_response_invalid";
interface StatusContext {
  record: string;
  status: string;
}

type Level = "INFO" | "WARNING" | "ERROR";

/** Serialize the allowed event/context fields and route the entry to its severity channel. */
function emit(level: Level, event: FrontendEvent, context?: StatusContext): void {
  const entry = JSON.stringify({
    timestamp: new Date().toISOString(),
    level,
    event,
    ...(context ? { record: context.record, status: context.status } : {}),
  });

  if (level === "ERROR") {
    console.error(entry);
  } else if (level === "WARNING") {
    console.warn(entry);
  } else {
    console.info(entry);
  }
}

export const logger = {
  info: (event: FrontendEvent): void => emit("INFO", event),
  warning: (
    ...args:
      | [event: Exclude<FrontendEvent, "unknown_status">]
      | [event: "unknown_status", context: StatusContext]
  ): void => emit("WARNING", args[0], args[1]),
  error: (event: FrontendEvent): void => emit("ERROR", event),
};
