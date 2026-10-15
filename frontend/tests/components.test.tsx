import { fireEvent, render, screen } from "./render";
import { describe, expect, it, vi } from "vitest";
import { Modal } from "@/components/Modal";
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
