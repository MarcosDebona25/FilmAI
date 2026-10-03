import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Modal } from "@/components/Modal";
import { ReviewCard } from "@/components/ReviewCard";
import { ReviewModal } from "@/components/ReviewModal";
import type { MiResena } from "@/lib/reviews";
import { apiFetch } from "@/lib/api";
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }));
const item: MiResena = {
  id: 1,
  id_tmdb: 10,
  tipo: "movie",
  titulo: "Interstellar",
  poster: "/p.jpg",
  valor: 8,
  fecha: "2026-10-03",
  texto: "Muy buena",
};
describe("modal accesible", () => {
  it("abre con nombre, permite Escape y devuelve el foco", () => {
    const button = document.createElement("button");
    document.body.append(button);
    button.focus();
    const close = vi.fn();
    const view = render(
      <Modal title="Prueba" onClose={close}>
        <button>Cancelar</button>
      </Modal>
    );
    expect(screen.getByRole("dialog", { name: "Prueba" })).toHaveAttribute("open");
    fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
    expect(close).toHaveBeenCalledOnce();
    view.unmount();
    expect(button).toHaveFocus();
    button.remove();
  });
  it("no cierra con Escape durante un envío", () => {
    const close = vi.fn();
    render(
      <Modal title="Prueba" busy onClose={close}>
        Enviando
      </Modal>
    );
    fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
    expect(close).not.toHaveBeenCalled();
  });
});
describe("tarjeta de reseña", () => {
  it("distingue la nota de la fecha con una estrella y etiqueta accesible", () => {
    render(<ReviewCard item={item} onAction={vi.fn()} />);
    const rating = screen.getByLabelText("Calificación: 8 de 10");
    expect(rating).toHaveTextContent("8/10");
    expect(rating.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByText("3/10/2026")).toBeVisible();
  });
  it.each([48, 72])(
    "oculta Leer más cuando el texto ocupa %s px y cabe en tres líneas",
    (height) => {
      const computedStyle = window.getComputedStyle;
      vi.spyOn(window, "getComputedStyle").mockImplementation((element) => {
        const style = computedStyle(element);
        style.lineHeight = "24px";
        return style;
      });
      vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(height);
      render(<ReviewCard item={item} onAction={vi.fn()} />);
      expect(screen.queryByRole("button", { name: /Leer más|Leer menos/ })).not.toBeInTheDocument();
    }
  );

  it("muestra póster y reemplazo si falla, expande texto y separa acciones", async () => {
    const action = vi.fn();
    const computedStyle = window.getComputedStyle;
    vi.spyOn(window, "getComputedStyle").mockImplementation((element) => {
      const style = computedStyle(element);
      style.lineHeight = "24px";
      return style;
    });
    vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(120);
    render(<ReviewCard item={item} onAction={action} />);
    fireEvent.error(screen.getByAltText("Póster de Interstellar"));
    expect(screen.getByRole("img", { name: "Sin póster de Interstellar" })).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Leer más" }));
    expect(screen.getByRole("button", { name: "Leer menos" })).toHaveAttribute(
      "aria-expanded",
      "true"
    );
    for (const [label, value] of [
      ["Editar", "edit"],
      ["Eliminar reseña", "text"],
      ["Quitar calificación", "rating"],
    ]) {
      await userEvent.click(screen.getByRole("button", { name: label }));
      expect(action).toHaveBeenLastCalledWith(value);
    }
  });
  it("mantiene calificaciones sin texto y no ofrece borrar una reseña inexistente", () => {
    render(<ReviewCard item={{ ...item, texto: null, poster: "" }} onAction={vi.fn()} />);
    expect(screen.getByRole("note")).toHaveTextContent("Todavía no escribiste una reseña.");
    expect(screen.getByRole("note").querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(screen.queryByRole("button", { name: "Eliminar reseña" })).not.toBeInTheDocument();
  });
});
describe("gestión de reseñas", () => {
  it("precarga y envía cambios de nota y texto", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ ...item, valor: 9, texto: "Nueva" });
    const success = vi.fn();
    render(<ReviewModal item={item} action="edit" onClose={vi.fn()} onSuccess={success} />);
    expect(screen.getByRole("radio", { name: "8 de 10" })).toBeChecked();
    expect(
      screen.getByRole("dialog", { name: 'Editar calificación y reseña de "Interstellar"' })
    ).toBeVisible();
    expect(screen.getByLabelText("Reseña (opcional)")).toHaveFocus();
    expect(screen.getByRole("radio", { name: "1 de 10" })).not.toHaveFocus();
    await userEvent.click(screen.getByRole("radio", { name: "9 de 10" }));
    await userEvent.clear(screen.getByLabelText("Reseña (opcional)"));
    await userEvent.type(screen.getByLabelText("Reseña (opcional)"), "Nueva");
    await userEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    expect(apiFetch).toHaveBeenCalledWith("/api/reviews/1/", {
      method: "PUT",
      body: { valor: 9, texto: "Nueva" },
    });
    expect(success).toHaveBeenCalled();
  });
  it.each(["text", "rating"] as const)(
    "confirma el borrado %s usando su ruta y resultado",
    async (action) => {
      vi.mocked(apiFetch).mockResolvedValue(undefined);
      const success = vi.fn();
      render(<ReviewModal item={item} action={action} onClose={vi.fn()} onSuccess={success} />);
      await userEvent.click(
        screen.getByRole("button", {
          name: action === "text" ? "Eliminar reseña" : "Quitar calificación",
        })
      );
      expect(apiFetch).toHaveBeenCalledWith(`/api/reviews/1/${action === "text" ? "texto/" : ""}`, {
        method: "DELETE",
      });
      expect(success).toHaveBeenCalledWith(action === "text" ? { ...item, texto: null } : null);
    }
  );
  it("no envía al cancelar", async () => {
    vi.mocked(apiFetch).mockClear();
    const close = vi.fn();
    render(<ReviewModal item={item} action="rating" onClose={close} onSuccess={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(close).toHaveBeenCalledOnce();
    expect(apiFetch).not.toHaveBeenCalled();
  });
  it("conserva el modal y permite reintentar tras un fallo", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("network")).mockResolvedValue(undefined);
    const success = vi.fn();
    render(<ReviewModal item={item} action="text" onClose={vi.fn()} onSuccess={success} />);
    await userEvent.click(screen.getByRole("button", { name: "Eliminar reseña" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Tus datos se mantienen");
    expect(success).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Eliminar reseña" }));
    await waitFor(() => expect(success).toHaveBeenCalled());
  });
});

it("Tab y Mayús+Tab recorren el grupo de estrellas seleccionado dentro del modal", () => {
  render(<ReviewModal item={item} action="edit" onClose={vi.fn()} onSuccess={vi.fn()} />);
  const last = screen.getByRole("button", { name: "Actualizar" });
  last.focus();
  fireEvent.keyDown(last, { key: "Tab" });
  expect(screen.getByRole("radio", { name: "8 de 10" })).toHaveFocus();
  fireEvent.keyDown(screen.getByRole("radio", { name: "8 de 10" }), { key: "Tab", shiftKey: true });
  expect(last).toHaveFocus();
});
it("un envío pendiente deshabilita acciones y no permite un segundo borrado", async () => {
  let finish!: () => void;
  vi.mocked(apiFetch)
    .mockClear()
    .mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = () => resolve(undefined);
        })
    );
  render(<ReviewModal item={item} action="text" onClose={vi.fn()} onSuccess={vi.fn()} />);
  const button = screen.getByRole("button", { name: "Eliminar reseña" });
  await userEvent.click(button);
  expect(button).toBeDisabled();
  await userEvent.click(button);
  expect(apiFetch).toHaveBeenCalledOnce();
  finish();
  await waitFor(() => expect(button).toBeEnabled());
});
