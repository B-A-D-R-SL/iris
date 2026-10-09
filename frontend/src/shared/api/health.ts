export interface HealthResponse {
  status: "ok";
}

export async function getHealthStatus(): Promise<HealthResponse> {
  const response = await fetch("/api/health/");

  if (!response.ok) {
    throw new Error(`Backend unavailable: ${response.status}`);
  }

  const data: unknown = await response.json();

  if (typeof data !== "object" || data === null || !("status" in data) || data.status !== "ok") {
    throw new Error("Invalid backend health response");
  }

  return { status: "ok" };
}
