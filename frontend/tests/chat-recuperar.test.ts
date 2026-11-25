import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ apiFetch: vi.fn() }));
vi.mock("@/lib/api", async (original) => ({ ...(await original()), ...api }));

import { buscarTurnoGuardado, ESPERA_RECUPERACION_MS, TOPE_RECUPERACION_MS } from "@/lib/chat";

/** Como la API: de más nuevo a más viejo. */
const pagina = (...results: object[]) => ({ next: null, results });
const P = (id: number, texto = "hola") => ({ id, autor: "usuario", texto });
const R = (id: number) => ({ id, autor: "chatbot", texto: "Hola", tarjetas: [] });

describe("buscarTurnoGuardado", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    api.apiFetch.mockReset();
  });
  afterEach(() => void vi.useRealTimers());

  it("encuentra la pareja nueva en el primer intento", async () => {
    api.apiFetch.mockResolvedValue(pagina(R(8), P(7), R(4), P(3)));
    const pareja = await buscarTurnoGuardado("hola", 4, () => true);
    expect(pareja?.map((m) => m.id)).toEqual([7, 8]);
    expect(api.apiFetch).toHaveBeenCalledTimes(1);
  });

  it("la misma pregunta ya respondida antes no cuenta, ni otra pregunta nueva", async () => {
    api.apiFetch.mockResolvedValue(pagina(R(8), P(7, "otra"), R(4), P(3)));
    const busqueda = buscarTurnoGuardado("hola", 4, () => true);
    await vi.advanceTimersByTimeAsync(ESPERA_RECUPERACION_MS);
    expect(await busqueda).toBeNull();
    expect(api.apiFetch).toHaveBeenCalledTimes(2);
  });

  it("si todavía se estaba guardando, la encuentra en el segundo intento", async () => {
    api.apiFetch
      .mockResolvedValueOnce(pagina(R(4), P(3)))
      .mockResolvedValueOnce(pagina(R(8), P(7), R(4), P(3)));
    const busqueda = buscarTurnoGuardado("hola", 4, () => true);
    await vi.advanceTimersByTimeAsync(ESPERA_RECUPERACION_MS);
    expect((await busqueda)?.map((m) => m.id)).toEqual([7, 8]);
  });

  it("sin red no insiste", async () => {
    api.apiFetch.mockRejectedValue(new Error("sin red"));
    expect(await buscarTurnoGuardado("hola", 4, () => true)).toBeNull();
    expect(api.apiFetch).toHaveBeenCalledTimes(1);
  });

  it("un pedido colgado se abandona al llegar al tope", async () => {
    api.apiFetch.mockReturnValue(new Promise(() => {}));
    const busqueda = buscarTurnoGuardado("hola", 4, () => true);
    await vi.advanceTimersByTimeAsync(TOPE_RECUPERACION_MS);
    expect(await busqueda).toBeNull();
  });

  it("si el turno se canceló durante la espera, no vuelve a pedir", async () => {
    api.apiFetch.mockResolvedValue(pagina());
    let vigente = true;
    const busqueda = buscarTurnoGuardado("hola", 4, () => vigente);
    await vi.advanceTimersByTimeAsync(1);
    vigente = false;
    await vi.advanceTimersByTimeAsync(ESPERA_RECUPERACION_MS);
    expect(await busqueda).toBeNull();
    expect(api.apiFetch).toHaveBeenCalledTimes(1);
  });
});
