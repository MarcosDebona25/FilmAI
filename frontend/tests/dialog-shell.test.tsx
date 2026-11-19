import { fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DialogShell } from "@/components/features/title/DialogShell";
import { render, screen } from "./render";

/**
 * Cerrar al tocar el fondo es opcional (19/11/2026): en calificar, reseñar o
 * renombrar, un toque sin querer fuera de la caja borraría lo escrito.
 */
function abrir(props: { cerrarConFondo?: boolean }) {
  const onClose = vi.fn();
  render(
    <DialogShell labelledBy="titulo" onClose={onClose} {...props}>
      <h2 id="titulo">Diálogo</h2>
    </DialogShell>,
    { locale: "en" }
  );
  const dialogo = screen.getByRole("dialog");
  // jsdom no hace layout: se le da una caja para distinguir «fuera» de «dentro».
  vi.spyOn(dialogo, "getBoundingClientRect").mockReturnValue({
    left: 100,
    right: 500,
    top: 100,
    bottom: 400,
  } as DOMRect);
  return { dialogo, onClose };
}

describe("DialogShell: tocar el fondo", () => {
  it("por defecto no cierra, así no se pierde lo escrito", () => {
    const { dialogo, onClose } = abrir({});

    fireEvent.click(dialogo, { clientX: 20, clientY: 20 });

    expect(onClose).not.toHaveBeenCalled();
  });

  it("con `cerrarConFondo` cierra al tocar fuera de la caja, y no adentro", () => {
    const { dialogo, onClose } = abrir({ cerrarConFondo: true });

    fireEvent.click(dialogo, { clientX: 110, clientY: 110 });
    expect(onClose).not.toHaveBeenCalled();

    fireEvent.click(dialogo, { clientX: 20, clientY: 20 });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
