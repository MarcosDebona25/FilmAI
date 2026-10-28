import { describe, expect, it } from "vitest";
import { esperaLegible, translateError } from "@/lib/errors";

describe("esperaLegible", () => {
  it.each([
    [1, "throttledWithWait", { retryAfterSeconds: 1 }],
    [59, "throttledWithWait", { retryAfterSeconds: 59 }],
    [60, "throttledWithWaitMinutes", { minutes: 1 }],
    [61, "throttledWithWaitMinutes", { minutes: 2 }],
    [3540, "throttledWithWaitMinutes", { minutes: 59 }],
    [3541, "throttledWithWaitHours", { hours: 1 }],
    [3600, "throttledWithWaitHours", { hours: 1 }],
    [3601, "throttledWithWaitHours", { hours: 2 }],
    [7200, "throttledWithWaitHours", { hours: 2 }],
  ])("%i s → %s", (segundos, key, params) => {
    expect(esperaLegible(segundos)).toEqual({ key, params });
  });
});

describe("translateError con 429 (Too Many Requests)", () => {
  const throttled = (segundos: number) => ({
    code: "throttled",
    params: { retry_after_seconds: segundos },
  });

  it("en español usa segundos, minutos u horas según la espera", () => {
    expect(translateError(throttled(30), "es")).toContain("30 segundos");
    expect(translateError(throttled(1), "es")).toContain("1 segundo.");
    expect(translateError(throttled(90), "es")).toContain("2 minutos");
    expect(translateError(throttled(60), "es")).toContain("1 minuto.");
    expect(translateError(throttled(3600), "es")).toContain("1 hora.");
    expect(translateError(throttled(7000), "es")).toContain("2 horas");
  });

  it("en inglés usa las mismas unidades", () => {
    expect(translateError(throttled(30), "en")).toContain("30 seconds");
    expect(translateError(throttled(120), "en")).toContain("2 minutes");
    expect(translateError(throttled(3600), "en")).toContain("1 hour.");
    expect(translateError(throttled(10800), "en")).toContain("3 hours");
  });

  it("nunca muestra miles de segundos", () => {
    expect(translateError(throttled(3600), "es")).not.toMatch(/3600|3\.600/);
  });

  it("sin espera conocida usa el mensaje genérico", () => {
    expect(translateError({ code: "throttled" }, "es")).toBe(
      "Hay demasiadas solicitudes. Intentá de nuevo más tarde."
    );
  });
});

describe("translateError con review_moderated (409 Conflict)", () => {
  it("se traduce por código en ambos idiomas", () => {
    expect(translateError({ code: "review_moderated" }, "es")).toBe(
      "Esta reseña fue moderada, así que no podés editar ni borrar su texto."
    );
    expect(translateError({ code: "review_moderated" }, "en")).toBe(
      "This review was moderated, so you can’t edit or delete its text."
    );
  });
});
