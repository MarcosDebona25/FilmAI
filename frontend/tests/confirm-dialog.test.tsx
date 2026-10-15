import { describe, expect, it, vi } from "vitest";

import { ConfirmDialog } from "@/components/features/title/ConfirmDialog";
import { fireEvent, render, screen, waitFor } from "./render";

describe("ConfirmDialog", () => {
  const props = {
    titulo: "Remove your rating?",
    descripcion: "Your rating of Interstellar and your review will be deleted.",
    confirmar: "Remove rating",
    onCancel: vi.fn(),
  };

  it("es un alertdialog con su texto y el foco arranca en Cancelar", () => {
    render(<ConfirmDialog {...props} onConfirm={vi.fn()} />, { locale: "en" });

    const dialogo = screen.getByRole("alertdialog", { name: "Remove your rating?" });
    expect(dialogo).toHaveAccessibleDescription(
      "Your rating of Interstellar and your review will be deleted."
    );
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
  });

  it("muestra la reseña que se va a perder", () => {
    render(<ConfirmDialog {...props} preview="La vi tres veces." onConfirm={vi.fn()} />, {
      locale: "en",
    });

    expect(screen.getByText("La vi tres veces.").tagName).toBe("BLOCKQUOTE");
  });

  it("mientras confirma deshabilita los botones y avisa el error si falla", async () => {
    let fallar: (motivo: Error) => void = () => {};
    const onConfirm = vi.fn(() => new Promise<void>((_, rechazar) => (fallar = rechazar)));
    render(<ConfirmDialog {...props} onConfirm={onConfirm} />, { locale: "en" });

    fireEvent.click(screen.getByRole("button", { name: "Remove rating" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled());
    fallar(new Error("Something went wrong. Try again later."));

    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong.");
    expect(screen.getByRole("button", { name: "Remove rating" })).toBeEnabled();
  });
});
