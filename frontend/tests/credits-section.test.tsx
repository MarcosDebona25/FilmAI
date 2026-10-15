import { describe, expect, it } from "vitest";

import { CreditsSection } from "@/components/features/title/CreditsSection";
import { render, screen } from "./render";

const reparto = Array.from({ length: 4 }, (_, i) => ({
  nombre: `Persona ${i + 1}`,
  personaje: `Personaje ${i + 1}`,
}));

describe("Dirección y reparto", () => {
  it("con director, el reparto va en la columna de la derecha", () => {
    render(<CreditsSection creditos={{ directores: ["Hayao Miyazaki"], reparto }} tipo="movie" />);
    const grilla = screen.getByText("Hayao Miyazaki").closest("div")!.parentElement!;
    expect(grilla.className).toContain("md:grid-cols-[240px_minmax(0,1fr)]");
  });

  it("sin director, el reparto ocupa todo el ancho", () => {
    // Pasa en muchas series y animes: antes quedaba apretado en la columna de 240 px.
    render(<CreditsSection creditos={{ directores: [], reparto }} tipo="tv" />);
    const lista = screen.getByRole("list");
    expect(lista.parentElement!.parentElement!.className).not.toContain("240px");
    expect(lista.className).toContain("xl:grid-cols-4");
    expect(screen.getAllByRole("listitem")).toHaveLength(4);
  });
});
