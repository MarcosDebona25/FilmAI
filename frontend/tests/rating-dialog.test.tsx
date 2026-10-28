import { describe, expect, it, vi } from "vitest";

import { RatingDialog } from "@/components/features/title/RatingDialog";
import { fireEvent, render, screen, waitFor } from "./render";

const base = { titulo: "Interstellar", onClose: vi.fn() };

describe("RatingDialog al calificar", () => {
  it("no deja publicar sin nota y avisa que la suma a Vistas", () => {
    render(<RatingDialog {...base} enVistas={false} onSubmit={vi.fn()} />, { locale: "en" });

    expect(screen.getByRole("dialog", { name: "Rate Interstellar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Post" })).toBeDisabled();
    expect(screen.getByText("Rating Interstellar also adds it to Watched.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove rating" })).toBeNull();

    fireEvent.click(screen.getByRole("radio", { name: "8 out of 10" }));
    expect(screen.getByRole("button", { name: "Post" })).toBeEnabled();
  });

  it("si ya está en Vistas no repite el aviso", () => {
    render(<RatingDialog {...base} enVistas onSubmit={vi.fn()} />, { locale: "en" });

    expect(screen.queryByText(/also adds it to Watched/)).toBeNull();
  });

  it("si está en Watchlist, avisa que calificar también la saca de ahí", () => {
    render(<RatingDialog {...base} enVistas={false} enPendientes onSubmit={vi.fn()} />, {
      locale: "en",
    });

    expect(
      screen.getByText("Rating Interstellar also adds it to Watched and removes it from Watchlist.")
    ).toBeInTheDocument();
  });

  it("cuenta los caracteres, limita a 1000 y manda nota y texto sin espacios de más", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<RatingDialog {...base} enVistas={false} onSubmit={onSubmit} />, { locale: "en" });
    const texto = screen.getByRole("textbox", { name: /Review/ });

    expect(texto).toHaveAttribute("maxLength", "1000");
    fireEvent.change(texto, { target: { value: "  Una obra.  " } });
    expect(screen.getByText("13/1000")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "9 out of 10" }));
    fireEvent.click(screen.getByRole("button", { name: "Post" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith({ valor: 9, texto: "Una obra." }));
  });

  it("si la API falla, muestra el error y no se cierra", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("The catalog couldn’t respond."));
    render(<RatingDialog {...base} enVistas={false} onSubmit={onSubmit} />, { locale: "en" });

    fireEvent.click(screen.getByRole("radio", { name: "7 out of 10" }));
    fireEvent.click(screen.getByRole("button", { name: "Post" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The catalog couldn’t respond.");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(base.onClose).not.toHaveBeenCalled();
  });
});

describe("RatingDialog al editar", () => {
  const inicial = { valor: 9, texto: "La vi tres veces." };

  it("precarga nota y texto, muestra la nota anterior al cambiarla y ofrece quitarla", () => {
    const onRemoveRating = vi.fn();
    render(
      <RatingDialog
        {...base}
        enVistas
        inicial={inicial}
        onSubmit={vi.fn()}
        onRemoveRating={onRemoveRating}
      />,
      { locale: "es" }
    );

    expect(screen.getByRole("dialog", { name: "Editar calificación" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "9 de 10" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("textbox", { name: /Reseña/ })).toHaveValue("La vi tres veces.");
    expect(screen.queryByText(/Antes:/)).toBeNull();

    fireEvent.click(screen.getByRole("radio", { name: "6 de 10" }));
    expect(screen.getByText(/Antes:/)).toHaveTextContent("Antes: 9");

    fireEvent.click(screen.getByRole("button", { name: "Quitar calificación" }));
    expect(onRemoveRating).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Actualizar" })).toBeEnabled();
  });

  it("Cerrar avisa sin publicar", () => {
    const onClose = vi.fn();
    const onSubmit = vi.fn();
    render(
      <RatingDialog {...base} onClose={onClose} enVistas inicial={inicial} onSubmit={onSubmit} />,
      { locale: "en" }
    );

    fireEvent.click(screen.getByRole("button", { name: "Close" }));

    expect(onClose).toHaveBeenCalled();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

describe("RatingDialog con la reseña moderada", () => {
  const inicial = { valor: 9, texto: "La vi tres veces.", moderada: true };

  it("deja el texto de solo lectura y explica por qué", () => {
    render(<RatingDialog {...base} enVistas inicial={inicial} onSubmit={vi.fn()} />, {
      locale: "es",
    });

    const texto = screen.getByRole("textbox", { name: /Reseña/ });
    expect(texto).toHaveAttribute("readonly");
    expect(texto).toHaveValue("La vi tres veces.");
    const aviso = screen.getByText(
      "Esta reseña fue moderada, así que no podés editar ni borrar su texto."
    );
    expect(texto).toHaveAccessibleDescription(aviso.textContent ?? "");
    expect(screen.queryByText(/\/1000/)).toBeNull();
  });

  it("la nota se puede cambiar y el texto viaja tal cual estaba", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<RatingDialog {...base} enVistas inicial={inicial} onSubmit={onSubmit} />, {
      locale: "es",
    });

    fireEvent.change(screen.getByRole("textbox", { name: /Reseña/ }), {
      target: { value: "Intento de cambio." },
    });
    fireEvent.click(screen.getByRole("radio", { name: "5 de 10" }));
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({ valor: 5, texto: "La vi tres veces." })
    );
  });

  it("sin moderar, el texto sigue siendo editable", () => {
    render(
      <RatingDialog
        {...base}
        enVistas
        inicial={{ ...inicial, moderada: false }}
        onSubmit={vi.fn()}
      />,
      { locale: "es" }
    );

    expect(screen.getByRole("textbox", { name: /Reseña/ })).not.toHaveAttribute("readonly");
    expect(screen.queryByText(/fue moderada/)).toBeNull();
  });
});
