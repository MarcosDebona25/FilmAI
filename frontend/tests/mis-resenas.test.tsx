import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { MisResenas } from "@/components/MisResenas";
import { apiFetch } from "@/lib/api";
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }));
vi.mock("@/components/AccountProvider", () => ({
  useAccount: () => ({ perfil: { pk: 1 }, cargando: false, error: null }),
}));
const item = {
  id: 1,
  id_tmdb: 10,
  tipo: "movie",
  titulo: "Interstellar",
  poster: "",
  valor: 8,
  fecha: "2026-10-03",
  texto: "Muy buena",
};
beforeEach(() => vi.mocked(apiFetch).mockReset());
it("muestra carga y luego calificaciones sin texto", async () => {
  vi.mocked(apiFetch).mockResolvedValue({ results: [{ ...item, texto: null }], next: null });
  render(<MisResenas />);
  expect(screen.getByRole("status")).toBeInTheDocument();
  expect(await screen.findByText("Todavía no escribiste una reseña.")).toBeVisible();
});
it("permite reintentar la carga inicial", async () => {
  vi.mocked(apiFetch)
    .mockRejectedValueOnce(new Error("network"))
    .mockResolvedValue({ results: [item], next: null });
  render(<MisResenas />);
  expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos cargar");
  await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
  expect(await screen.findByRole("article")).toBeVisible();
});
it("deduplica páginas y mantiene el listado si la siguiente falla", async () => {
  vi.mocked(apiFetch)
    .mockResolvedValueOnce({ results: [item], next: "http://backend/api/reviews/mias/?cursor=a" })
    .mockRejectedValueOnce(new Error("network"))
    .mockResolvedValue({ results: [item, { ...item, id: 2, titulo: "Dark" }], next: null });
  render(<MisResenas />);
  await screen.findByRole("article");
  await userEvent.click(screen.getByRole("button", { name: "Cargar más" }));
  await screen.findByRole("alert");
  expect(screen.getAllByRole("article")).toHaveLength(1);
  await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
  await screen.findByRole("heading", { name: "Dark" });
  expect(screen.getAllByRole("article")).toHaveLength(2);
});
it("eliminar texto mantiene la tarjeta y borrar nota muestra vacío", async () => {
  vi.mocked(apiFetch)
    .mockResolvedValueOnce({ results: [item], next: null })
    .mockResolvedValue(undefined);
  render(<MisResenas />);
  await screen.findByRole("article");
  await userEvent.click(screen.getByRole("button", { name: "Eliminar reseña" }));
  fireEvent.click(screen.getByRole("dialog").querySelector("button:last-child")!);
  expect(await screen.findByText("Todavía no escribiste una reseña.")).toBeVisible();
  expect(screen.getAllByRole("article")).toHaveLength(1);
  await userEvent.click(screen.getByRole("button", { name: "Quitar calificación" }));
  fireEvent.click(screen.getByRole("dialog").querySelector("button:last-child")!);
  expect(
    await screen.findByText("Todavía no calificaste ninguna producción ni escribiste reseñas.")
  ).toBeVisible();
});
