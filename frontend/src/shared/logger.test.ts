// AI contribution: 50% or more AI-generated
import { afterEach, describe, expect, it, vi } from "vitest";

import { logger } from "./logger";

describe("privacy-safe frontend logger", () => {
  afterEach(() => vi.restoreAllMocks());

  it("emits structured warning events without arbitrary data", () => {
    const spy = vi.spyOn(console, "warn").mockImplementation(() => {});

    logger.warning("backend_health_unavailable");

    expect(spy).toHaveBeenCalledOnce();
    const entry: unknown = JSON.parse(String(spy.mock.calls[0]?.[0]));
    expect(entry).toMatchObject({ level: "WARNING", event: "backend_health_unavailable" });
    expect(Object.keys(entry as Record<string, unknown>).sort()).toEqual([
      "event",
      "level",
      "timestamp",
    ]);
  });
});
