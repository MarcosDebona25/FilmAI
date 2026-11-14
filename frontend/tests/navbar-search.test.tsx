import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NavbarSearch } from "@/components/NavbarSearch";
import { ApiError } from "@/lib/api";
import { limpiarCacheSugerencias } from "@/lib/sugerencias";
import en from "@/messages/en/common.json";
import { act, fireEvent, render, screen, within } from "./render";

/**
 * La lupa de la navbar y su combobox de sugerencias. El backend se reemplaza por
 * un `apiFetch` de mentira: cada test decide qué contesta `suggest/`.
 */
const router = vi.hoisted(() => ({ push: vi.fn() }));
const api = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/home",
}));
vi.mock("next/image", () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ alt }: { alt: string }) => <img alt={alt} />,
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: api.apiFetch,
}));

/** Recorte de una respuesta real de `suggest/?q=nolan` (13/11/2026). */
const RESPUESTA = {
  results: [
    {
      media_type: "person",
      id: 525,
      name: "Christopher Nolan",
      rol: "director",
      gender: 2,
      profile_path: "/x.jpg",
    },
    {
      media_type: "movie",
      id: 27205,
      title: "Inception",
      release_date: "2010-07-15",
      poster_path: "/y.jpg",
      vote_average: 8.4,
    },
    {
      media_type: "tv",
      id: 70523,
      name: "Dark",
      first_air_date: "2017-12-01",
      poster_path: null,
      vote_average: 8.4,
    },
  ],
};

const ESPERA = 250;

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  limpiarCacheSugerencias();
  api.apiFetch.mockResolvedValue(structuredClone(RESPUESTA));
});
afterEach(() => {
  vi.useRealTimers();
});

const lupa = () => screen.getByRole("button", { name: en.nav.search.openLabel, hidden: true });
const campo = () => screen.getByRole("combobox");

function abrir() {
  render(<NavbarSearch />, { locale: "en" });
  fireEvent.click(lupa());
}

/** Escribe y deja pasar la espera (el debounce) y la respuesta del pedido. */
async function escribir(texto: string) {
  fireEvent.change(campo(), { target: { value: texto } });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ESPERA);
  });
}

describe("la lupa", () => {
  it("cerrada es solo un botón con su nombre, su atajo y sin campo", () => {
    render(<NavbarSearch />, { locale: "en" });

    expect(lupa()).toHaveAttribute("aria-expanded", "false");
    expect(lupa()).toHaveAttribute("aria-keyshortcuts", "/");
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("al tocarla despliega el campo y le da el foco", () => {
    abrir();

    expect(lupa()).toHaveAttribute("aria-expanded", "true");
    expect(campo()).toHaveFocus();
    expect(campo()).toHaveAttribute("placeholder", en.nav.search.placeholder);
    // El campo está dentro de un <search> con su etiqueta, al que apunta la lupa.
    // jsdom no conoce el rol de <search>: se lo busca por la etiqueta.
    const buscador = screen.getByLabelText(en.nav.search.label, { selector: "search" });
    expect(lupa()).toHaveAttribute("aria-controls", buscador.id);
  });

  it("el combobox cumple ARIA 1.2: lista asociada y sin opción activa al empezar", () => {
    abrir();

    expect(campo()).toHaveAttribute("aria-autocomplete", "list");
    expect(campo()).toHaveAttribute("aria-expanded", "false");
    expect(campo()).not.toHaveAttribute("aria-activedescendant");
  });
});

describe("sugerencias", () => {
  it("con 1 carácter no pide nada; desde 2 espera 250 ms y hace un solo pedido", async () => {
    abrir();
    fireEvent.change(campo(), { target: { value: "n" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(ESPERA * 2);
    });
    expect(api.apiFetch).not.toHaveBeenCalled();

    fireEvent.change(campo(), { target: { value: "no" } });
    fireEvent.change(campo(), { target: { value: "nol" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(ESPERA - 60);
    });
    expect(api.apiFetch).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(api.apiFetch).toHaveBeenCalledTimes(1);
    expect(api.apiFetch.mock.calls[0][0]).toBe("/api/catalogo/suggest/?q=nol");
  });

  it("las muestra agrupadas: personas, títulos con tipo y año, y «ver todos» al final", async () => {
    abrir();
    await escribir("nol");

    expect(campo()).toHaveAttribute("aria-expanded", "true");
    const lista = screen.getByRole("listbox");
    const personas = within(lista).getByRole("group", { name: en.nav.search.groupPeople });
    const titulos = within(lista).getByRole("group", { name: en.nav.search.groupTitles });
    expect(within(personas).getByRole("option")).toHaveTextContent("Christopher Nolan");
    expect(within(personas).getByRole("option")).toHaveTextContent("Director");
    const opciones = within(titulos).getAllByRole("option");
    expect(opciones[0]).toHaveTextContent("Inception");
    expect(opciones[0]).toHaveTextContent("Movie · 2010");
    expect(opciones[1]).toHaveTextContent("TV show · 2017");
    const todas = within(lista).getAllByRole("option");
    expect(todas.at(-1)).toHaveTextContent("See all results for “nol”");
  });

  it("anuncia cuántas hay en una región viva", async () => {
    abrir();
    await escribir("nol");

    expect(screen.getByRole("status")).toHaveTextContent("3 suggestions");
  });

  it("un texto ya visto en la sesión sale de la caché, sin otro pedido", async () => {
    abrir();
    await escribir("nol");
    await escribir("nola");
    api.apiFetch.mockClear();

    await escribir("nol");

    expect(api.apiFetch).not.toHaveBeenCalled();
    expect(screen.getByRole("listbox")).toBeInTheDocument();
  });

  it("descarta la respuesta de un texto viejo que llega tarde", async () => {
    const pendientes: ((valor: unknown) => void)[] = [];
    api.apiFetch.mockImplementation(() => new Promise((resolver) => pendientes.push(resolver)));
    abrir();
    await escribir("nol");
    await escribir("dun");
    // Llega primero la del texto nuevo y después la vieja.
    await act(async () => {
      pendientes[1]({
        results: [{ media_type: "movie", id: 438631, title: "Dune", release_date: "2021-09-15" }],
      });
      pendientes[0](structuredClone(RESPUESTA));
    });

    expect(screen.getByRole("option", { name: /Dune/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Inception/ })).not.toBeInTheDocument();
  });

  it("si el pedido falla cierra la lista en silencio y Enter sigue yendo a Buscar", async () => {
    api.apiFetch.mockRejectedValue(
      new ApiError(429, { code: "throttled", params: {}, errors: [] })
    );
    abrir();
    await escribir("nol");

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    fireEvent.keyDown(campo(), { key: "Enter" });
    expect(router.push).toHaveBeenCalledWith("/search?q=nol");
  });
});

describe("teclado", () => {
  it("↓ recorre las opciones con aria-activedescendant y vuelve al campo; ↑ desde el campo va a la última", async () => {
    abrir();
    await escribir("nol");

    fireEvent.keyDown(campo(), { key: "ArrowDown" });
    expect(campo()).toHaveAttribute("aria-activedescendant", "sug-person-525");
    expect(screen.getByRole("option", { name: /Christopher Nolan/ })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    fireEvent.keyDown(campo(), { key: "ArrowDown" });
    expect(campo()).toHaveAttribute("aria-activedescendant", "sug-movie-27205");
    fireEvent.keyDown(campo(), { key: "ArrowDown" });
    fireEvent.keyDown(campo(), { key: "ArrowDown" });
    expect(campo()).toHaveAttribute("aria-activedescendant", "sug-all");
    // Pasada la última, vuelve al campo: ninguna opción activa.
    fireEvent.keyDown(campo(), { key: "ArrowDown" });
    expect(campo()).not.toHaveAttribute("aria-activedescendant");
    fireEvent.keyDown(campo(), { key: "ArrowUp" });
    expect(campo()).toHaveAttribute("aria-activedescendant", "sug-all");
  });

  it("escribir no mueve la opción activa (selección manual)", async () => {
    abrir();
    await escribir("nol");
    fireEvent.keyDown(campo(), { key: "ArrowDown" });

    await escribir("nola");

    expect(campo()).toHaveAttribute("aria-activedescendant", "sug-person-525");
  });

  it("Enter sobre un título va a su ficha, sin origen, y deja la lupa cerrada y vacía", async () => {
    abrir();
    await escribir("nol");
    fireEvent.keyDown(campo(), { key: "ArrowDown" });
    fireEvent.keyDown(campo(), { key: "ArrowDown" });

    fireEvent.keyDown(campo(), { key: "Enter" });

    expect(router.push).toHaveBeenCalledWith("/movie/27205");
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(lupa()).toHaveAttribute("aria-expanded", "false");
  });

  it("Enter sin opción activa busca el texto en Buscar", async () => {
    abrir();
    await escribir("nolan ");

    fireEvent.keyDown(campo(), { key: "Enter" });

    expect(router.push).toHaveBeenCalledWith("/search?q=nolan");
  });

  it("Escape cierra la lista; un segundo Escape vacía, pliega y devuelve el foco a la lupa", async () => {
    abrir();
    await escribir("nol");

    fireEvent.keyDown(campo(), { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(campo()).toHaveValue("nol");

    fireEvent.keyDown(campo(), { key: "Escape" });
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(lupa()).toHaveFocus();
  });

  it("Tab cierra la lista sin elegir nada", async () => {
    abrir();
    await escribir("nol");

    fireEvent.keyDown(campo(), { key: "Tab" });

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(router.push).not.toHaveBeenCalled();
  });

  it("Alt+↓ vuelve a abrir la lista con la última respuesta", async () => {
    abrir();
    await escribir("nol");
    fireEvent.keyDown(campo(), { key: "Escape" });

    fireEvent.keyDown(campo(), { key: "ArrowDown", altKey: true });

    expect(screen.getByRole("listbox")).toBeInTheDocument();
    expect(campo()).not.toHaveAttribute("aria-activedescendant");
  });
});

describe("ratón y cierre", () => {
  it("elegir una persona va a Buscar con ella como filtro", async () => {
    abrir();
    await escribir("nol");

    const opcion = screen.getByRole("option", { name: /Christopher Nolan/ });
    // El clic no le saca el foco al campo: `mousedown` se cancela.
    expect(fireEvent.mouseDown(opcion)).toBe(false);
    fireEvent.click(opcion);

    expect(router.push).toHaveBeenCalledWith("/search?person=525&role=director");
  });

  it("«Ver todos los resultados» lleva a Buscar con el texto", async () => {
    abrir();
    await escribir("nol");

    fireEvent.click(screen.getByRole("option", { name: /See all results/ }));

    expect(router.push).toHaveBeenCalledWith("/search?q=nol");
  });

  it("el botón ✕ cierra, borra el texto y devuelve el foco a la lupa", async () => {
    abrir();
    await escribir("nol");

    fireEvent.click(screen.getByRole("button", { name: en.nav.search.closeLabel }));

    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(lupa()).toHaveFocus();
  });

  it("perder el foco sin texto la pliega; con texto queda desplegada y sin lista", async () => {
    abrir();
    fireEvent.blur(campo());
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();

    fireEvent.click(lupa());
    await escribir("nol");
    fireEvent.blur(campo());

    expect(campo()).toHaveValue("nol");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});

describe("atajo /", () => {
  // jsdom no trae `matchMedia`: lo simulamos con un ancho de escritorio o de celular.
  function anchoDeEscritorio(esEscritorio: boolean) {
    vi.stubGlobal("matchMedia", (consulta: string) => ({
      matches: esEscritorio,
      media: consulta,
      addEventListener: () => {},
      removeEventListener: () => {},
    }));
  }
  beforeEach(() => anchoDeEscritorio(true));
  afterEach(() => vi.unstubAllGlobals());

  it("en celular no hace nada: la lupa está oculta y la tecla se escribe", () => {
    anchoDeEscritorio(false);
    render(<NavbarSearch />, { locale: "en" });

    const evento = new KeyboardEvent("keydown", { key: "/", bubbles: true, cancelable: true });
    document.body.dispatchEvent(evento);

    expect(evento.defaultPrevented).toBe(false);
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("despliega la lupa y enfoca el campo", () => {
    render(<NavbarSearch />, { locale: "en" });

    fireEvent.keyDown(document.body, { key: "/" });

    expect(campo()).toHaveFocus();
  });

  it("se ignora si el foco está en un campo de texto o hay un diálogo abierto", () => {
    render(
      <>
        <NavbarSearch />
        <input aria-label="otro" />
      </>,
      { locale: "en" }
    );

    fireEvent.keyDown(screen.getByLabelText("otro"), { key: "/" });
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();

    const dialogo = document.createElement("dialog");
    dialogo.setAttribute("open", "");
    document.body.append(dialogo);
    fireEvent.keyDown(document.body, { key: "/" });
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    dialogo.remove();
  });
});
