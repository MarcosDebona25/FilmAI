import { describe, expect, it } from "vitest";

import { MediaCard } from "@/components/features/MediaCard";
import { normalizeTitle, type Title } from "@/lib/catalog";
import { fireEvent, render, screen } from "./render";
import { insidious, reacher } from "./catalog-fixtures";

const pelicula = normalizeTitle(insidious) as Title;
const serie = normalizeTitle(reacher) as Title;

describe("MediaCard", () => {
  it("lleva a la ficha y muestra tipo, año y nota en inglés", () => {
    render(<MediaCard title={pelicula} showType />, { locale: "en" });

    const link = screen.getByRole("link", { name: /Insidious: Out of the Further/ });
    expect(link).toHaveAttribute("href", "/movie/1291595");
    expect(link).toHaveTextContent("Movie · 2026");
    expect(link).toHaveTextContent("7.7");
    expect(screen.getByText("TMDB rating: 7.7 out of 10")).toBeInTheDocument();
    expect(screen.getByAltText("Insidious: Out of the Further poster")).toBeInTheDocument();
  });

  it("en español usa coma decimal y las etiquetas del catálogo", () => {
    render(<MediaCard title={serie} showType />, { locale: "es" });

    const link = screen.getByRole("link", { name: /Reacher/ });
    expect(link).toHaveAttribute("href", "/tv/108978");
    expect(link).toHaveTextContent("Serie · 2022");
    expect(screen.getByText("Calificación TMDB: 8,1 de 10")).toBeInTheDocument();
  });

  it("sin el tipo muestra solo el año (selector en Movies o TV shows)", () => {
    render(<MediaCard title={pelicula} showType={false} />, { locale: "en" });

    const link = screen.getByRole("link");
    expect(link).toHaveTextContent("2026");
    expect(link).not.toHaveTextContent("Movie");
  });

  it("sin póster, o si la imagen falla, muestra el reemplazo", () => {
    const { unmount } = render(<MediaCard title={{ ...pelicula, poster: null }} showType />, {
      locale: "en",
    });
    expect(screen.getByText("No poster")).toBeInTheDocument();
    unmount();

    render(<MediaCard title={pelicula} showType />, { locale: "en" });
    fireEvent.error(screen.getByAltText("Insidious: Out of the Further poster"));
    expect(screen.getByText("No poster")).toBeInTheDocument();
  });

  it("sin nota no muestra la estrella", () => {
    render(<MediaCard title={{ ...pelicula, nota: null }} showType />, { locale: "en" });

    expect(screen.queryByText(/TMDB rating/)).not.toBeInTheDocument();
  });

  it("un título completado en inglés lleva lang=en", () => {
    render(<MediaCard title={{ ...pelicula, tituloEnIngles: true }} showType />, {
      locale: "es",
    });

    expect(screen.getByText("Insidious: Out of the Further")).toHaveAttribute("lang", "en");
  });

  it("con la fecha de agregado a una lista la muestra numérica según el idioma", () => {
    const { unmount } = render(
      <MediaCard title={pelicula} showType addedAt="2026-10-18T12:00:00Z" />,
      {
        locale: "es",
      }
    );
    expect(screen.getByText("18/10/2026")).toBeInTheDocument();
    expect(screen.getByText("Agregada a esta lista el 18/10/2026")).toBeInTheDocument();
    unmount();

    render(<MediaCard title={pelicula} showType addedAt="2026-10-18T12:00:00Z" />, {
      locale: "en",
    });
    expect(screen.getByText("10/18/2026")).toBeInTheDocument();
    expect(screen.getByText("Added to this list on 10/18/2026")).toBeInTheDocument();
  });

  it("sin fecha de agregado no muestra ninguna", () => {
    render(<MediaCard title={pelicula} showType />, { locale: "en" });
    expect(document.querySelector("time")).toBeNull();
  });
});
