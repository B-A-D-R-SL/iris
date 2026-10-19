// AI contribution: 50% or more AI-generated
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Docker uses the backend service name; host-native development uses localhost.
const apiTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
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
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/test/**", "src/**/*.test.{ts,tsx}"],
      reporter: ["text", "lcov"],
    },
  },
});
