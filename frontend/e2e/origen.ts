/** Origen del servidor de e2e; sigue a `E2E_PORT` igual que playwright.config.ts. */
export const ORIGIN = `http://127.0.0.1:${process.env.E2E_PORT ?? "3100"}`;
