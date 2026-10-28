// AI contribution: 50% or more AI-generated
import type { RootOptions } from "react-dom/client";

/**
 * React prints every error caught by an error boundary with console.error(error),
 * even in production, and the message can contain personal data (SEC-09).
 * AppErrorBoundary already logs a generic event, so React logs nothing more.
 */
export const rootOptions: RootOptions = {
  onCaughtError: () => {},
};
