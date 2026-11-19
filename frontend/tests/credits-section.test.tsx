import { describe, expect, it } from "vitest";

import { CreditsSection } from "@/components/features/title/CreditsSection";
import { render, screen } from "./render";

const reparto = Array.from({ length: 4 }, (_, i) => ({
  id: 100 + i,
  nombre: `Persona ${i + 1}`,
  personaje: `Personaje ${i + 1}`,
}));

describe("Dirección y reparto", () => {
  it("con director, el reparto va en la columna de la derecha", () => {
    render(
      <CreditsSection
        creditos={{ directores: [{ id: 608, nombre: "Hayao Miyazaki" }], reparto }}
        tipo="movie"
      />
    );
    const grilla = screen.getByText("Hayao Miyazaki").closest("div")!.parentElement!;
    expect(grilla.className).toContain("md:grid-cols-[15rem_minmax(0,1fr)]");
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Dirección y reparto");
  });

  it("sin director, el reparto ocupa todo el ancho", () => {
    // Pasa en muchas series y animes: antes quedaba apretado en la columna de 240 px.
    render(<CreditsSection creditos={{ directores: [], reparto }} tipo="tv" />);
    const lista = screen.getByRole("list");
    expect(lista.parentElement!.parentElement!.className).not.toContain("240px");
    expect(lista.className).toContain("xl:grid-cols-4");
    expect(screen.getAllByRole("listitem")).toHaveLength(4);
    // El título dice lo que hay, sin repetir «Reparto» como etiqueta.
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Reparto");
    expect(screen.getAllByText("Reparto")).toHaveLength(1);
  });

  it("cada nombre lleva a Buscar con esa persona: director o creador como director, reparto como actor", () => {
    const directores = [
      { id: 608, nombre: "Hayao Miyazaki" },
      { id: 1417, nombre: "Isao Takahata" },
    ];
    const { unmount } = render(<CreditsSection creditos={{ directores, reparto }} tipo="movie" />);

    expect(screen.getByRole("link", { name: "Hayao Miyazaki" })).toHaveAttribute(
      "href",
      "/search?person=608&role=director"
    );
    expect(screen.getByRole("link", { name: "Isao Takahata" })).toHaveAttribute(
      "href",
      "/search?person=1417&role=director"
    );
    // Los nombres siguen separados por coma, fuera de los enlaces.
    expect(screen.getByText(/Hayao Miyazaki/).closest("div")).toHaveTextContent(
      "Hayao Miyazaki, Isao Takahata"
    );
    // El enlace es solo el nombre: el personaje queda afuera.
    expect(screen.getByRole("link", { name: "Persona 1" })).toHaveAttribute(
      "href",
      "/search?person=100&role=actor"
    );
    unmount();

    // En series, los creadores también van como «director» (es el rol que Buscar conoce).
    render(<CreditsSection creditos={{ directores, reparto: [] }} tipo="tv" />);
    expect(screen.getByRole("link", { name: "Isao Takahata" })).toHaveAttribute(
      "href",
      "/search?person=1417&role=director"
    );
  });

  it("sin id de TMDB el nombre queda como texto, sin enlace", () => {
    render(
      <CreditsSection
        creditos={{
          directores: [{ id: null, nombre: "Hayao Miyazaki" }],
          reparto: [{ id: null, nombre: "Persona 1", personaje: "Personaje 1" }],
        }}
        tipo="movie"
      />
    );

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("Hayao Miyazaki")).toBeInTheDocument();
    expect(screen.getByText("Persona 1")).toBeInTheDocument();
  });

  it("el nombre con enlace lleva un subrayado fijo; sin enlace, no", () => {
    // En celular no hay hover: el subrayado es la señal de que se puede tocar.
    render(
      <CreditsSection
        creditos={{
          directores: [{ id: null, nombre: "Sin Enlace" }],
          reparto: [{ id: 100, nombre: "Con Enlace", personaje: "X" }],
        }}
        tipo="movie"
      />
    );
    expect(screen.getByRole("link", { name: "Con Enlace" })).toHaveClass("underline");
    expect(screen.getByText("Sin Enlace")).not.toHaveClass("underline");
  });
});
