import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "@/lib/api";
import {
  borrarTextoDeResena,
  crearCalificacion,
  editarCalificacion,
  quitarCalificacion,
} from "@/lib/review-actions";

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }));

const llamadas = () => vi.mocked(apiFetch).mock.calls;

beforeEach(() => {
  vi.mocked(apiFetch).mockReset();
});

describe("crearCalificacion", () => {
  it("manda un POST sin texto y avisa que se publicó la nota", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ id: 1 });
    const resultado = await crearCalificacion({ idTmdb: 603, tipo: "movie", valor: 8, texto: "" });
    expect(llamadas()[0]).toEqual([
      "/api/reviews/",
      { method: "POST", body: { id_tmdb: 603, tipo: "movie", valor: 8 } },
    ]);
    expect(resultado).toEqual({ creada: { id: 1 }, aviso: "ratingPublished" });
  });

  it("con texto lo manda y avisa que se publicó la reseña", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ id: 1 });
    const resultado = await crearCalificacion({ idTmdb: 1, tipo: "tv", valor: 5, texto: "Bien" });
    expect(llamadas()[0][1]).toMatchObject({ body: { texto: "Bien" } });
    expect(resultado.aviso).toBe("ratingReviewPublished");
  });
});

describe("editarCalificacion", () => {
  const previa = { id: 7, valor: 6, texto: "Vieja" };

  it("cambiar solo la nota es un PUT con la nota", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ valor: 9 });
    const resultado = await editarCalificacion(previa, 9, "Vieja");
    expect(llamadas()).toEqual([["/api/reviews/7/", { method: "PUT", body: { valor: 9 } }]]);
    expect(resultado.respuesta).toEqual({ valor: 9 });
    expect(resultado.aviso).toBe("ratingUpdated");
  });

  it("vaciar el texto es un DELETE aparte y no hay PUT", async () => {
    vi.mocked(apiFetch).mockResolvedValue(undefined);
    const resultado = await editarCalificacion(previa, 6, "  ");
    expect(llamadas()).toEqual([["/api/reviews/7/texto/", { method: "DELETE" }]]);
    expect(resultado.plan.borrarTexto).toBe(true);
    expect(resultado.respuesta).toBeNull();
    expect(resultado.aviso).toBe("reviewDeleted");
  });

  it("nota y texto nuevo juntos avisan de ambos", async () => {
    vi.mocked(apiFetch).mockResolvedValue({});
    const resultado = await editarCalificacion(previa, 7, "Nueva");
    expect(llamadas()[0][1]).toMatchObject({ body: { valor: 7, texto: "Nueva" } });
    expect(resultado.aviso).toBe("ratingReviewUpdated");
  });

  it("solo el texto avisa que se actualizó la reseña", async () => {
    vi.mocked(apiFetch).mockResolvedValue({});
    expect((await editarCalificacion(previa, 6, "Otra")).aviso).toBe("reviewUpdated");
  });

  it("sin cambios no llama a la API ni avisa", async () => {
    const resultado = await editarCalificacion(previa, 6, "Vieja");
    expect(llamadas()).toHaveLength(0);
    expect(resultado).toMatchObject({ respuesta: null, aviso: null });
  });

  it("si la API falla, el error llega a la pantalla", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("falla"));
    await expect(editarCalificacion(previa, 9, "Vieja")).rejects.toThrow("falla");
  });
});

describe("borrarTextoDeResena", () => {
  it("borra solo el texto", async () => {
    vi.mocked(apiFetch).mockResolvedValue(undefined);
    expect(await borrarTextoDeResena(4)).toEqual({ aviso: "reviewDeleted" });
    expect(llamadas()).toEqual([["/api/reviews/4/texto/", { method: "DELETE" }]]);
  });
});

describe("quitarCalificacion", () => {
  it("el aviso depende de si tenía reseña", async () => {
    vi.mocked(apiFetch).mockResolvedValue(undefined);
    expect(await quitarCalificacion({ id: 3, texto: "x" })).toEqual({
      aviso: "ratingReviewDeleted",
    });
    expect(await quitarCalificacion({ id: 3, texto: null })).toEqual({ aviso: "ratingDeleted" });
    expect(llamadas()[0]).toEqual(["/api/reviews/3/", { method: "DELETE" }]);
  });
});
