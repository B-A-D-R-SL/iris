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
  | "partner_application_response_invalid"
  | "partner_application_request_failed"
  | "household_status_response_invalid";
interface StatusContext {
  record: string;
  status: string;
}

/** Events about a failed request: they carry its HTTP status code and nothing else. */
type HttpEvent = "listing_post_failed";
interface HttpContext {
  /** The response's status code, or null when no response arrived (connection lost). */
  statusCode: number | null;
}

type PlainEvent = Exclude<FrontendEvent, "unknown_status" | HttpEvent>;
type Level = "INFO" | "WARNING" | "ERROR";

/** Serialize the allowed event/context fields and route the entry to its severity channel. */
function emit(level: Level, event: FrontendEvent, context?: StatusContext | HttpContext): void {
  const entry = JSON.stringify({
    timestamp: new Date().toISOString(),
    level,
    event,
    ...(context && "record" in context ? { record: context.record, status: context.status } : {}),
    // Same key as the backend's request logs (docs/guides/observability.md).
    ...(context && "statusCode" in context ? { status_code: context.statusCode } : {}),
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
  info: (event: PlainEvent): void => emit("INFO", event),
  warning: (
    ...args:
      | [event: PlainEvent]
      | [event: "unknown_status", context: StatusContext]
      | [event: HttpEvent, context: HttpContext]
  ): void => emit("WARNING", args[0], args[1]),
  error: (...args: [event: PlainEvent] | [event: HttpEvent, context: HttpContext]): void =>
    emit("ERROR", args[0], args[1]),
};
