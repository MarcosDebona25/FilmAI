import { describe, expect, it, vi } from "vitest";

import { StarRating } from "@/components/features/title/StarRating";
import { fireEvent, render, screen } from "./render";

const estrellas = () => screen.getAllByRole("radio");

describe("StarRating", () => {
  it("son diez opciones con su nota y la elegida marcada", () => {
    render(<StarRating value={7} onChange={vi.fn()} label="Rating" />, { locale: "en" });

    expect(screen.getByRole("radiogroup", { name: "Rating" })).toBeInTheDocument();
    expect(estrellas()).toHaveLength(10);
    expect(screen.getByRole("radio", { name: "7 out of 10" })).toHaveAttribute(
      "aria-checked",
      "true"
    );
    expect(screen.getByRole("radio", { name: "6 out of 10" })).toHaveAttribute(
      "aria-checked",
      "false"
    );
  });

  it("un clic elige esa nota", () => {
    const onChange = vi.fn();
    render(<StarRating value={0} onChange={onChange} label="Rating" />, { locale: "es" });

    fireEvent.click(screen.getByRole("radio", { name: "8 de 10" }));

    expect(onChange).toHaveBeenCalledWith(8);
  });

  it("las flechas, Home y End cambian la nota sin pasarse de 1 a 10", () => {
    const onChange = vi.fn();
    render(<StarRating value={10} onChange={onChange} label="Rating" />, { locale: "en" });
    const elegida = screen.getByRole("radio", { name: "10 out of 10" });

    fireEvent.keyDown(elegida, { key: "ArrowLeft" });
    fireEvent.keyDown(elegida, { key: "ArrowRight" });
    fireEvent.keyDown(elegida, { key: "Home" });
    fireEvent.keyDown(elegida, { key: "End" });

    expect(onChange.mock.calls.map(([nota]) => nota)).toEqual([9, 10, 1, 10]);
  });

  it("solo la elegida entra en el orden de Tab; sin nota, la primera", () => {
    const { rerender } = render(<StarRating value={4} onChange={vi.fn()} label="Rating" />, {
      locale: "en",
    });
    expect(estrellas().filter((e) => e.tabIndex === 0)).toEqual([
      screen.getByRole("radio", { name: "4 out of 10" }),
    ]);

    rerender(<StarRating value={0} onChange={vi.fn()} label="Rating" />);
    expect(estrellas().filter((e) => e.tabIndex === 0)).toEqual([estrellas()[0]]);
  });

  it("al pasar el mouse previsualiza y deja tenues las que quedan afuera", () => {
    const onPreview = vi.fn();
    render(<StarRating value={7} onChange={vi.fn()} onPreview={onPreview} label="Rating" />, {
      locale: "en",
    });

    fireEvent.mouseEnter(screen.getByRole("radio", { name: "3 out of 10" }));

    expect(onPreview).toHaveBeenLastCalledWith(3);
    expect(estrellas().map((e) => e.dataset.estado)).toEqual([
      ...Array(3).fill("llena"),
      ...Array(4).fill("tenue"),
      ...Array(3).fill("vacia"),
    ]);

    fireEvent.mouseLeave(screen.getByRole("radiogroup"));
    expect(onPreview).toHaveBeenLastCalledWith(0);
  });
});
