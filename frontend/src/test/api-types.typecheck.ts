// AI contribution: 50% or more AI-generated
// Compile-time assertions included by the existing TypeScript check, not Vitest.
import type { paths } from "../shared/api/generated";

type HealthResponse = paths["/api/health/"]["get"]["responses"][200]["content"]["application/json"];

export const validHealthResponse: HealthResponse = { status: "ok" };

// @ts-expect-error The generated contract only accepts the status "ok".
export const invalidHealthResponse: HealthResponse = { status: "unavailable" };

// @ts-expect-error The generated contract requires a status field.
export const missingHealthStatus: HealthResponse = {};
