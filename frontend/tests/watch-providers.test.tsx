import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { WatchProviders } from "@/components/features/title/WatchProviders";
import type { Plataformas } from "@/lib/title";
import type { Pedido } from "@/lib/use-catalog";
import { render, screen, within } from "./render";
import { PLATAFORMAS_AR, PLATAFORMAS_CN } from "./title-fixtures";

const ok = (data: Plataformas): Pedido<Plataformas> => ({ status: "ok", data, error: null });

describe("WatchProviders", () => {
  it("con datos: línea con la cantidad de plataformas únicas y panel con los grupos", async () => {
    const user = userEvent.setup();
    render(<WatchProviders pedido={ok(PLATAFORMAS_AR)} pais="AR" />, { locale: "en" });

    // Netflix está en suscripción y en compra: cuenta una sola vez.
    const linea = screen.getByRole("button", { name: /Stream or rent/ });
    expect(linea).toHaveTextContent("3 options in Argentina");
    expect(linea).toHaveAttribute("aria-expanded", "false");
    expect(linea).toHaveAttribute("aria-haspopup", "dialog");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(linea);
    expect(linea).toHaveAttribute("aria-expanded", "true");
    const panel = screen.getByRole("dialog", { name: "Where to watch" });
    expect(within(panel).getByRole("heading", { name: "Stream" })).toBeInTheDocument();
    expect(within(panel).getByRole("heading", { name: "Rent" })).toBeInTheDocument();
    expect(within(panel).getByRole("heading", { name: "Buy" })).toBeInTheDocument();
    // Los grupos vacíos no aparecen.
    expect(within(panel).queryByRole("heading", { name: "Free" })).not.toBeInTheDocument();
    // Los logos llevan alt y title, y no son enlaces.
    const logo = within(panel).getAllByAltText("Netflix")[0];
    expect(logo).toHaveAttribute("title", "Netflix");
    expect(logo.closest("a")).toBeNull();
    expect(logo).toHaveAttribute("src", expect.stringContaining("image.tmdb.org/t/p/w92/"));
    const tmdb = within(panel).getByRole("link", { name: /See all options on TMDB/ });
    expect(tmdb).toHaveAttribute("href", PLATAFORMAS_AR.enlace);
    expect(tmdb).toHaveAttribute("target", "_blank");
    expect(tmdb).toHaveAttribute("rel", "noopener noreferrer");
    expect(within(panel).getByRole("link", { name: "JustWatch" })).toHaveAttribute(
      "href",
      "https://www.justwatch.com"
    );
    expect(panel).toHaveTextContent("Data by JustWatch");
  });

  it("el plural y el idioma salen del catálogo", () => {
    const una = { ...PLATAFORMAS_CN, pais: "AR", suscripcion: [PLATAFORMAS_AR.suscripcion[0]] };
    render(<WatchProviders pedido={ok(una)} pais="AR" />, { locale: "es" });
    expect(screen.getByRole("button", { name: /Ver o alquilar/ })).toHaveTextContent(
      "1 opción en Argentina"
    );
  });

  it("Escape cierra el panel y devuelve el foco a la línea", async () => {
    const user = userEvent.setup();
    render(<WatchProviders pedido={ok(PLATAFORMAS_AR)} pais="AR" />, { locale: "en" });
    const linea = screen.getByRole("button", { name: /Stream or rent/ });
    await user.click(linea);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(linea).toHaveFocus();
  });

  it("país sin datos: una línea explica que todavía no está disponible", () => {
    render(<WatchProviders pedido={ok(PLATAFORMAS_CN)} pais="CN" />, { locale: "en" });
    expect(
      screen.getByText("Not available to stream, rent or buy in China yet.")
    ).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("cargando: esqueleto estático con aviso para lectores de pantalla", () => {
    const { container } = render(
      <WatchProviders pedido={{ status: "loading", data: null, error: null }} pais="AR" />,
      { locale: "en" }
    );
    expect(screen.getByRole("status")).toHaveTextContent("Loading streaming options…");
    expect(container.querySelector(".animate-pulse")).toBeNull();
  });

  it("error o sin país: no muestra nada", () => {
    const { container, rerender } = render(
      <WatchProviders pedido={{ status: "error", data: null, error: new Error("x") }} pais="AR" />
    );
    expect(container).toBeEmptyDOMElement();
    rerender(<WatchProviders pedido={ok(PLATAFORMAS_AR)} pais={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
