import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { TmdbCredits } from "@/components/TmdbCredits";
import { render, screen } from "./render";

const AVISO_EN = "This product uses the TMDB API but is not endorsed or certified by TMDB.";
const AVISO_ES = "Este producto usa la API de TMDB, pero TMDB no lo respalda ni lo certifica.";

describe("créditos de TMDB en /terms", () => {
  it("en inglés: aviso exacto, logo con su alt, enlace al sitio y ancla #credits", () => {
    const { container } = render(<TmdbCredits />, { locale: "en" });

    expect(container.querySelector("section#credits")).not.toBeNull();
    expect(screen.getByRole("heading", { name: "Credits" })).toBeVisible();
    expect(screen.getByText(AVISO_EN)).toBeVisible();

    const logo = screen.getByRole("img", { name: "TMDB logo" });
    expect(logo.tagName).toBe("IMG");
    expect(logo).toHaveAttribute("src", "/tmdb/logo5.svg");
    const enlace = logo.closest("a");
    expect(enlace).toHaveAttribute("href", "https://www.themoviedb.org");
    expect(enlace).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("en español: aviso y alt traducidos", () => {
    render(<TmdbCredits />, { locale: "es" });
    expect(screen.getByRole("heading", { name: "Créditos" })).toBeVisible();
    expect(screen.getByText(AVISO_ES)).toBeVisible();
    expect(screen.getByRole("img", { name: "Logo de TMDB" })).toBeVisible();
  });

  it("el logo no se altera: sin filtros, sin colores y sin giros en sus clases ni su estilo", () => {
    render(<TmdbCredits />, { locale: "en" });
    const logo = screen.getByRole("img", { name: "TMDB logo" });
    expect(logo.getAttribute("style") ?? "").not.toMatch(/filter|color|transform|rotate|scale/i);
    expect(logo.className).not.toMatch(/filter|invert|brightness|grayscale|rotate|scale|text-/);
    // Solo la altura está fija: el ancho sigue a la proporción original.
    expect(logo.className).toContain("w-auto");
  });
});

describe("logo oficial de TMDB", () => {
  const raiz = path.resolve(__dirname, "../..");
  const publicos = path.join(raiz, "frontend/public/tmdb");
  const oficiales = path.join(raiz, "docs/tmdb-legales");

  it("hay al menos un logo publicado", () => {
    expect(readdirSync(publicos).filter((f) => f.endsWith(".svg"))).toContain("logo5.svg");
  });

  it("cada archivo de public/tmdb es idéntico, byte por byte, a su original en docs/tmdb-legales", () => {
    for (const nombre of readdirSync(publicos)) {
      const copia = readFileSync(path.join(publicos, nombre));
      const original = readFileSync(path.join(oficiales, nombre));
      expect(copia.equals(original), nombre).toBe(true);
    }
  });
});
