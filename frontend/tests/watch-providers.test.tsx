import { fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { WatchProviders } from "@/components/features/title/WatchProviders";
import type { Plataformas } from "@/lib/title";
import type { Pedido } from "@/lib/use-catalog";
import { render, screen, within } from "./render";
import { PLATAFORMAS_AR, PLATAFORMAS_CN } from "./title-fixtures";

const ok = (data: Plataformas): Pedido<Plataformas> => ({ status: "ok", data, error: null });

describe("WatchProviders", () => {
  it("con datos: la línea es un botón y abre un diálogo modal con los grupos", async () => {
    const user = userEvent.setup();
    render(<WatchProviders pedido={ok(PLATAFORMAS_AR)} pais="AR" />, { locale: "en" });

    // Netflix está en suscripción y en compra: cuenta una sola vez.
    const linea = screen.getByRole("button", { name: /Stream or rent/ });
    expect(linea).toHaveTextContent("3 options in Argentina");
    expect(linea).toHaveAttribute("aria-expanded", "false");
    expect(linea).toHaveAttribute("aria-haspopup", "dialog");
    expect(linea).toHaveClass("min-h-11");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(linea);
    expect(linea).toHaveAttribute("aria-expanded", "true");
    const panel = screen.getByRole("dialog", { name: "Where to watch" });
    expect(panel).toHaveAttribute("aria-modal", "true");
    // Etiquetado por su título visible, no por un `aria-label` suelto.
    const titulo = within(panel).getByRole("heading", { level: 2, name: "Where to watch" });
    expect(panel).toHaveAttribute("aria-labelledby", titulo.id);
    // Los grupos vacíos no aparecen (acá, Free).
    expect(
      within(panel)
        .getAllByRole("heading", { level: 3 })
        .map((h) => h.textContent)
    ).toEqual(["Stream", "Rent", "Buy"]);
    // Los logos llevan alt y title, sin nombre visible, y no son enlaces.
    const logo = within(panel).getAllByAltText("Netflix")[0];
    expect(logo).toHaveAttribute("title", "Netflix");
    expect(logo.closest("a")).toBeNull();
    expect(logo).toHaveAttribute("src", expect.stringContaining("image.tmdb.org/t/p/w92/"));
    expect(within(panel).queryByText("Netflix")).not.toBeInTheDocument();
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

  it("con gratuitas: los grupos van en el orden Stream, Free, Rent, Buy y suman al conteo", async () => {
    const user = userEvent.setup();
    const conGratis = {
      ...PLATAFORMAS_AR,
      gratis: [{ id: 73, nombre: "Tubi TV", logo: null }],
    };
    render(<WatchProviders pedido={ok(conGratis)} pais="AR" />, { locale: "en" });

    const linea = screen.getByRole("button", { name: /Stream or rent/ });
    expect(linea).toHaveTextContent("4 options in Argentina");
    await user.click(linea);
    const panel = screen.getByRole("dialog", { name: "Where to watch" });
    expect(
      within(panel)
        .getAllByRole("heading", { level: 3 })
        .map((h) => h.textContent)
    ).toEqual(["Stream", "Free", "Rent", "Buy"]);
    // Sin logo: la inicial, con el nombre como etiqueta accesible y tooltip.
    const tubi = within(within(panel).getByRole("region", { name: "Free" })).getByRole("img", {
      name: "Tubi TV",
    });
    expect(tubi).toHaveAttribute("title", "Tubi TV");
  });

  it("el botón de cerrar cierra el diálogo y devuelve el foco a la línea", async () => {
    const user = userEvent.setup();
    render(<WatchProviders pedido={ok(PLATAFORMAS_AR)} pais="AR" />, { locale: "en" });
    const linea = screen.getByRole("button", { name: /Stream or rent/ });
    await user.click(linea);
    const cerrar = within(screen.getByRole("dialog")).getByRole("button", { name: "Close" });
    expect(cerrar).toHaveClass("size-11");
    await user.click(cerrar);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(linea).toHaveAttribute("aria-expanded", "false");
    expect(linea).toHaveFocus();
  });

  it("el plural y el idioma salen del catálogo", () => {
    const una = { ...PLATAFORMAS_CN, pais: "AR", suscripcion: [PLATAFORMAS_AR.suscripcion[0]] };
    render(<WatchProviders pedido={ok(una)} pais="AR" />, { locale: "es" });
    expect(screen.getByRole("button", { name: /Ver o alquilar/ })).toHaveTextContent(
      "1 opción en Argentina"
    );
  });

  it("Escape cierra el diálogo y devuelve el foco a la línea", async () => {
    const user = userEvent.setup();
    render(<WatchProviders pedido={ok(PLATAFORMAS_AR)} pais="AR" />, { locale: "en" });
    const linea = screen.getByRole("button", { name: /Stream or rent/ });
    await user.click(linea);
    // jsdom no traduce Escape en el evento `cancel` del <dialog>: se dispara a mano.
    fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
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
