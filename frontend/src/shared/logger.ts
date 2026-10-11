// AI contribution: 50% or more AI-generated
/** Structured, privacy-safe frontend events. No arbitrary user data is accepted. */

type FrontendEvent = "language_changed" | "backend_health_unavailable";
type Level = "INFO" | "WARNING" | "ERROR";

function emit(level: Level, event: FrontendEvent): void {
  const entry = JSON.stringify({ timestamp: new Date().toISOString(), level, event });

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
  warning: (event: FrontendEvent): void => emit("WARNING", event),
  error: (event: FrontendEvent): void => emit("ERROR", event),
};
