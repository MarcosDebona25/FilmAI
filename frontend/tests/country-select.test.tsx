import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { CountrySelect } from "@/components/CountrySelect";
import { formatPais, paisesOrdenados, regionDelNavegador } from "@/lib/format";
import { elegirPais } from "./elegir-pais";
import { render, screen, within } from "./render";

function Probe({ onBlur = vi.fn() }: { onBlur?: () => void }) {
  const [pais, setPais] = useState("");
  return <CountrySelect value={pais} onChange={setPais} onBlur={onBlur} error={undefined} />;
}

describe("CountrySelect", () => {
  it("arranca vacío, con el texto de ayuda, aunque el navegador tenga región", () => {
    vi.spyOn(navigator, "language", "get").mockReturnValue("es-AR");
    render(<Probe />, { locale: "en" });
    const campo = screen.getByLabelText("Country");
    expect(campo).toHaveAttribute("role", "combobox");
    expect(campo).toHaveTextContent("Choose your country");
    expect(campo).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("al abrirse ofrece los 249 países con el nombre en el idioma activo y el foco en el buscador", async () => {
    const user = userEvent.setup();
    render(<Probe />, { locale: "es" });
    await user.click(screen.getByLabelText("País"));
    // Abierta, la lista también se llama «País»: se busca el campo por su rol.
    expect(screen.getByRole("combobox", { name: "País" })).toHaveAttribute("aria-expanded", "true");
    expect(within(screen.getByRole("listbox")).getAllByRole("option")).toHaveLength(249);
    expect(screen.getByRole("option", { name: "Alemania" })).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: "Buscar país" })).toHaveFocus();
  });

  it("elegir un país con un clic lo selecciona, cierra la lista y vuelve al campo", async () => {
    const user = userEvent.setup();
    render(<Probe />, { locale: "en" });
    await elegirPais(user, screen.getByLabelText("Country"), "Brazil");
    const campo = screen.getByLabelText("Country");
    expect(campo).toHaveTextContent("Brazil");
    expect(campo).toHaveFocus();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(document.querySelector('input[name="pais"]')).toHaveValue("BR");
  });

  it("busca sin tildes ni mayúsculas y elige con flechas y Enter", async () => {
    const user = userEvent.setup();
    render(<Probe />, { locale: "es" });
    await user.click(screen.getByLabelText("País"));
    await user.keyboard("peru");
    expect(screen.getAllByRole("option").map((opcion) => opcion.textContent)).toEqual(["Perú"]);
    await user.clear(screen.getByRole("searchbox"));
    await user.keyboard("ar");
    const buscador = screen.getByRole("searchbox");
    const primera = screen.getAllByRole("option")[0];
    expect(buscador).toHaveAttribute("aria-activedescendant", primera.id);
    await user.keyboard("{ArrowDown}");
    const segunda = screen.getAllByRole("option")[1];
    expect(buscador).toHaveAttribute("aria-activedescendant", segunda.id);
    await user.keyboard("{Enter}");
    expect(screen.getByLabelText("País")).toHaveTextContent(segunda.textContent!);
  });

  it("sin coincidencias lo dice", async () => {
    const user = userEvent.setup();
    render(<Probe />, { locale: "en" });
    await user.click(screen.getByLabelText("Country"));
    await user.keyboard("zzzz");
    expect(screen.queryAllByRole("option")).toHaveLength(0);
    expect(screen.getByRole("status")).toHaveTextContent("No countries match that name.");
  });

  it("escribir sobre el campo cerrado abre la lista y empieza a buscar", async () => {
    const user = userEvent.setup();
    render(<Probe />, { locale: "en" });
    screen.getByLabelText("Country").focus();
    await user.keyboard("j");
    expect(screen.getByRole("searchbox")).toHaveValue("j");
    expect(screen.getByRole("searchbox")).toHaveFocus();
  });

  it("Escape cierra sin elegir y devuelve el foco al campo", async () => {
    const user = userEvent.setup();
    render(<Probe />, { locale: "en" });
    await user.click(screen.getByLabelText("Country"));
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Country")).toHaveFocus();
    expect(screen.getByLabelText("Country")).toHaveTextContent("Choose your country");
  });

  it("un clic afuera cierra la lista", async () => {
    const user = userEvent.setup();
    render(
      <>
        <Probe />
        <p>afuera</p>
      </>,
      { locale: "en" }
    );
    await user.click(screen.getByLabelText("Country"));
    await user.click(screen.getByText("afuera"));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("muestra el error recibido y marca el campo", () => {
    render(<CountrySelect value="" onChange={vi.fn()} error="Choose a country to continue." />, {
      locale: "en",
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Choose a country to continue.");
    expect(screen.getByLabelText("Country")).toHaveAttribute("aria-invalid", "true");
  });

  it("recorrerlo con Tab no cuenta como salida; abrirlo y salir sí", async () => {
    const onBlur = vi.fn();
    const user = userEvent.setup();
    render(<Probe onBlur={onBlur} />, { locale: "en" });
    await user.tab();
    await user.tab();
    expect(onBlur).not.toHaveBeenCalled();
    await user.click(screen.getByLabelText("Country"));
    await user.tab();
    expect(onBlur).toHaveBeenCalledOnce();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});

describe("formatos de país", () => {
  it("nombra el país en cada idioma y ordena por nombre", () => {
    expect(formatPais("DE", "en")).toBe("Germany");
    expect(formatPais("DE", "es")).toBe("Alemania");
    const nombres = paisesOrdenados("en").map((pais) => pais.name);
    expect(nombres).toEqual([...nombres].sort((a, b) => a.localeCompare(b, "en")));
  });

  it("la región del navegador solo vale si es un país de la lista", () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["es-AR"]);
    expect(regionDelNavegador()).toBe("AR");
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["es", "en-XX"]);
    expect(regionDelNavegador()).toBeNull();
  });
});
