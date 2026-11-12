// AI contribution: 50% or more AI-generated
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Docker uses the backend service name; host-native development uses localhost.
const apiTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

/** Phone tunnels only when IRIS_ALLOW_TUNNELS=1 or IRIS_TUNNEL_HOST is set. */
function tunnelAllowedHosts(): string[] | undefined {
  const exact = process.env.IRIS_TUNNEL_HOST?.trim();
  if (exact) return [exact];
  if (process.env.IRIS_ALLOW_TUNNELS === "1") {
    return [".trycloudflare.com", ".ngrok-free.app", ".ngrok.io"];
  }
  return undefined;
}

const allowedHosts = tunnelAllowedHosts();

export default defineConfig({
  plugins: [react()],
  server: {
    ...(allowedHosts ? { allowedHosts } : {}),
    watch: { usePolling: process.env.IRIS_DOCKER === "1" },
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: false,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}", "scripts/usability/**/*.mjs"],
      exclude: ["src/test/**", "src/**/*.test.{ts,tsx}", "scripts/**/*.test.mjs"],
      reporter: ["text", ["lcov", { projectRoot: ".." }]],
    },
  },
});
