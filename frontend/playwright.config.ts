import { defineConfig } from "@playwright/test";

// Puerto configurable: dos worktrees pueden correr e2e a la
// vez sin que uno reutilice el servidor del otro (reuseExistingServer).
const port = process.env.E2E_PORT ?? "3100";
const origin = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  use: {
    baseURL: origin,
    browserName: "chromium",
    locale: "es-AR",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `npm run dev -- -p ${port}`,
    url: origin,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      NEXT_PUBLIC_API_URL: origin,
      NEXT_DIST_DIR: ".next-e2e",
      // Muestra el botón de Google; los specs que lo usan reemplazan el SDK.
      NEXT_PUBLIC_GOOGLE_CLIENT_ID: "e2e.apps.googleusercontent.com",
    },
  },
});
