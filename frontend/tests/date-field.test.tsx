import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { DateField } from "@/components/access/DateField";
import type { AppLocale } from "@/i18n/config";
import { formatDateInput, maskDateInput, parseDateInput } from "@/lib/format";
import { useValidation } from "@/lib/use-validation";
import { maxFechaNacimiento, validarFechaNacimiento } from "@/lib/validation";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";

const copias = { en, es };

/** Formulario mínimo: guarda el ISO y valida como las pantallas de registro. */
function Formulario() {
  const [valor, setValor] = useState("");
  const [sucio, setSucio] = useState(false);
  const { validarFechaNacimiento: validar } = useValidation();
  return (
    <>
      <DateField
        label="Fecha"
        name="fecha_nacimiento"
        value={valor}
        onChange={(iso) => {
          setValor(iso);
          setSucio(true);
        }}
        error={sucio ? validar(valor) : null}
      />
      <output data-testid="iso">{valor}</output>
    </>
  );
}

function conIdioma(locale: AppLocale) {
  return (
    <NextIntlClientProvider locale={locale} messages={copias[locale]}>
      <Formulario />
    </NextIntlClientProvider>
  );
}

function montar(locale: AppLocale) {
  const user = userEvent.setup();
  const vista = render(conIdioma(locale));
  return { user, vista, campo: screen.getByLabelText("Fecha") as HTMLInputElement };
}

const iso = () => screen.getByTestId("iso").textContent;

describe("lib/format: fecha del campo según el idioma", () => {
  it("el mismo ISO se escribe con el orden de cada idioma", () => {
    expect(formatDateInput("1992-04-10", "es")).toBe("10/04/1992");
    expect(formatDateInput("1992-04-10", "en")).toBe("04/10/1992");
  });

  it("el mismo texto son fechas distintas en cada idioma", () => {
    expect(parseDateInput("10/04/1992", "es")).toBe("1992-04-10");
    expect(parseDateInput("10/04/1992", "en")).toBe("1992-10-04");
  });

  it("incompleto o inexistente devuelve null", () => {
    expect(parseDateInput("10/04/19", "es")).toBeNull();
    expect(parseDateInput("31/02/1992", "es")).toBeNull();
    expect(parseDateInput("02/31/1992", "en")).toBeNull();
    expect(parseDateInput("29/02/2000", "es")).toBe("2000-02-29");
  });

  it("la máscara pone las barras y completa con cero", () => {
    expect(maskDateInput("10", true)).toBe("10/");
    expect(maskDateInput("10", false)).toBe("10");
    expect(maskDateInput("10041992", false)).toBe("10/04/1992");
    expect(maskDateInput("4/", true)).toBe("04/");
    expect(maskDateInput("ab10x04", true)).toBe("10/04/");
    expect(maskDateInput("100419921", false)).toBe("10/04/1992");
  });
});

describe("lib/validation: fecha de nacimiento", () => {
  it("una fecha que no existe ya no pasa al mes siguiente", () => {
    expect(validarFechaNacimiento("1992-02-31")).toBe("date_inexistent");
  });

  it("el máximo del calendario usa la fecha local, no la UTC", () => {
    const hoy = new Date();
    const esperado = new Date(hoy);
    esperado.setFullYear(hoy.getFullYear() - 13);
    const [year, month, day] = maxFechaNacimiento().split("-").map(Number);
    expect([year, month, day]).toEqual([
      esperado.getFullYear(),
      esperado.getMonth() + 1,
      esperado.getDate(),
    ]);
  });
});

describe("DateField", () => {
  it("en español tipea DD/MM/AAAA y entrega el ISO", async () => {
    const { user, campo } = montar("es");
    expect(campo).toHaveAttribute("placeholder", "DD/MM/AAAA");
    await user.type(campo, "10041992");
    expect(campo).toHaveValue("10/04/1992");
    expect(iso()).toBe("1992-04-10");
  });

  it("en inglés los mismos dígitos son otra fecha", async () => {
    const { user, campo } = montar("en");
    expect(campo).toHaveAttribute("placeholder", "MM/DD/YYYY");
    await user.type(campo, "10041992");
    expect(campo).toHaveValue("10/04/1992");
    expect(iso()).toBe("1992-10-04");
  });

  it.each([
    ["10/04/1992", "10/04/1992"],
    ["10041992", "10/04/1992"],
    ["1992-04-10", "10/04/1992"],
  ])("pegar «%s» deja «%s»", async (pegado, visible) => {
    const { user, campo } = montar("es");
    await user.click(campo);
    await user.paste(pegado);
    expect(campo).toHaveValue(visible);
    expect(iso()).toBe("1992-04-10");
  });

  it("a mitad del tipeo no muestra error ni entrega valor", async () => {
    const { user, campo } = montar("es");
    await user.type(campo, "1004");
    expect(campo).toHaveValue("10/04/");
    expect(iso()).toBe("");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(campo).not.toHaveAttribute("aria-invalid");
  });

  it("incompleto al salir del campo avisa que la fecha no es válida", async () => {
    const { user, campo } = montar("es");
    await user.type(campo, "1004");
    await user.tab();
    expect(screen.getByRole("alert")).toHaveTextContent(es.errors.fields.fecha_nacimiento.invalid);
  });

  it("31/02 muestra el error específico de fecha inexistente", async () => {
    const { user, campo } = montar("es");
    await user.type(campo, "31021992");
    expect(screen.getByRole("alert")).toHaveTextContent(es.errors.codes.date_inexistent);
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(iso()).toBe("");
  });

  it("una fecha futura da birth_date_in_future", async () => {
    const { user, campo } = montar("es");
    await user.type(campo, `0101${new Date().getFullYear() + 1}`);
    expect(screen.getByRole("alert")).toHaveTextContent(es.errors.codes.birth_date_in_future);
  });

  it("menos de 13 años da minimum_age", async () => {
    const { user, campo } = montar("en");
    await user.type(campo, `0101${new Date().getFullYear() - 5}`);
    expect(screen.getByRole("alert")).toHaveTextContent(/at least 13 years/);
  });

  it("el calendario abre en enero de 2000, en español y desde el lunes", async () => {
    const { user, campo } = montar("es");
    const boton = screen.getByRole("button", { name: es.common.fields.openCalendar });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    await user.click(boton);
    const dialogo = screen.getByRole("dialog");
    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(boton).toHaveAttribute("aria-controls", dialogo.id);
    // La cabecera de días es decorativa (aria-hidden); su etiqueta dice qué día abre la semana.
    expect(dialogo.querySelector("th")).toHaveAttribute("aria-label", "lunes");

    await user.click(dialogo.querySelector('button[data-day="2000-01-15"]') as HTMLElement);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(campo).toHaveValue("15/01/2000");
    expect(campo).toHaveFocus();
    expect(iso()).toBe("2000-01-15");
  });

  it("en inglés el calendario empieza el domingo y escribe MM/DD/YYYY", async () => {
    const { user, campo } = montar("en");
    await user.click(screen.getByRole("button", { name: en.common.fields.openCalendar }));
    const dialogo = screen.getByRole("dialog");
    // La cabecera de días es decorativa (aria-hidden); su etiqueta dice qué día abre la semana.
    expect(dialogo.querySelector("th")).toHaveAttribute("aria-label", "Sunday");
    await user.click(dialogo.querySelector('button[data-day="2000-01-15"]') as HTMLElement);
    expect(campo).toHaveValue("01/15/2000");
  });

  it("con valor, abre en ese mes y deshabilita lo posterior a hoy − 13 años", async () => {
    const { user, campo } = montar("es");
    const max = maxFechaNacimiento();
    const [year, month, day] = max.split("-").map(Number);
    await user.type(campo, formatDateInput(max, "es").replace(/\//g, ""));
    await user.click(screen.getByRole("button", { name: es.common.fields.openCalendar }));
    const dialogo = screen.getByRole("dialog");
    expect(dialogo.querySelector(`button[data-day="${max}"]`)).toBeEnabled();
    const siguiente = new Date(year, month - 1, day + 1);
    // Si el día siguiente cae en otro mes, se ve como día de afuera; igual tiene que estar deshabilitado.
    const isoSiguiente = `${siguiente.getFullYear()}-${String(siguiente.getMonth() + 1).padStart(2, "0")}-${String(siguiente.getDate()).padStart(2, "0")}`;
    const celda = dialogo.querySelector(`button[data-day="${isoSiguiente}"]`);
    if (celda) expect(celda).toBeDisabled();
  });

  it("Escape cierra el calendario y devuelve el foco al campo", async () => {
    const { user, campo } = montar("es");
    await user.click(screen.getByRole("button", { name: es.common.fields.openCalendar }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(campo).toHaveFocus();
  });

  it("un clic afuera cierra el calendario", async () => {
    const { user } = montar("es");
    await user.click(screen.getByRole("button", { name: es.common.fields.openCalendar }));
    await user.click(document.body);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("cambiar el idioma cambia el placeholder y el orden", async () => {
    const { user, vista, campo } = montar("es");
    await user.type(campo, "10041992");
    vista.rerender(conIdioma("en"));
    expect(campo).toHaveAttribute("placeholder", "MM/DD/YYYY");
    expect(campo).toHaveValue("04/10/1992");
    expect(iso()).toBe("1992-04-10");
  });
});
