import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { CountrySelect } from "@/components/CountrySelect";
import { formatPais, paisesOrdenados, regionDelNavegador } from "@/lib/format";
import { render, screen } from "./render";

function Probe({ onBlur = vi.fn() }: { onBlur?: () => void }) {
  const [pais, setPais] = useState("");
  return <CountrySelect value={pais} onChange={setPais} onBlur={onBlur} error={undefined} />;
}

describe("CountrySelect", () => {
  it("arranca vacío, con la opción por defecto deshabilitada, aunque el navegador tenga región", () => {
    vi.spyOn(navigator, "language", "get").mockReturnValue("es-AR");
    render(<Probe />, { locale: "en" });
    expect(screen.getByLabelText("Country")).toHaveValue("");
    expect(screen.getByRole("option", { name: "Choose your country" })).toBeDisabled();
  });

  it("ofrece los 249 países con el nombre en el idioma activo", () => {
    render(<Probe />, { locale: "es" });
    expect(screen.getByLabelText("País")).toBeInTheDocument();
    expect(screen.getAllByRole("option")).toHaveLength(250);
    expect(screen.getByRole("option", { name: "Alemania" })).toHaveValue("DE");
  });

  it("elegir un país lo selecciona", async () => {
    render(<Probe />, { locale: "en" });
    await userEvent.selectOptions(screen.getByLabelText("Country"), "BR");
    expect(screen.getByLabelText("Country")).toHaveValue("BR");
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
    await user.tab({ shift: true });
    await user.click(screen.getByLabelText("Country"));
    await user.tab();
    expect(onBlur).toHaveBeenCalledOnce();
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
