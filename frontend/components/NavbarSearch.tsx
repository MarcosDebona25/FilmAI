"use client";

import { useEffect, useId, useRef, useState, type FocusEvent, type KeyboardEvent } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { CornerDownLeft, Search, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { tmdbLoader } from "@/lib/catalog";
import { routes } from "@/lib/routes";
import { MAX_TEXTO, urlDePersona, urlDeTexto } from "@/lib/search";
import {
  ESPERA_SUGERENCIAS_MS,
  MIN_CARACTERES,
  esAtajoDeBusqueda,
  pedirSugerencias,
  sugerenciasEnCache,
  type Sugerencia,
} from "@/lib/sugerencias";
import { cn } from "@/lib/utils";

type SugerenciaPersona = Extract<Sugerencia, { tipo: "person" }>;
type SugerenciaTitulo = Exclude<Sugerencia, SugerenciaPersona>;

/** Una fila de la lista: una sugerencia o el «Ver todos los resultados» del final. */
type Fila = { id: string; sugerencia: Sugerencia | null };

const idDe = (sugerencia: Sugerencia) => `sug-${sugerencia.tipo}-${sugerencia.id}`;
const ID_VER_TODO = "sug-all";

/**
 * La lupa de la navbar de escritorio (14/11/2026, variante «Lupa que se
 * expande» que eligió Gonza). Cerrada es un botón; al tocarla (o con «/») se
 * despliega un campo en el mismo lugar, con sugerencias de personas y títulos.
 *
 * Es un combobox ARIA 1.2 como `CountrySelect`, pero con un `<input>` editable
 * («lista con selección manual», APG): el foco se queda siempre en el campo y
 * la opción activa se señala con `aria-activedescendant`. Escribir nunca elige
 * nada por el usuario.
 *
 * Cómo se cierra: Esc (la primera vez cierra la lista; la segunda, el campo),
 * la ✕, o perder el foco sin texto. Con texto, perder el foco deja el campo
 * desplegado (el texto no se tira) y la lista cerrada.
 *
 * Los pedidos: 250 ms después de la última tecla y desde 2 caracteres, cada
 * pedido cancela al anterior, y una respuesta que llega tarde (de un texto que
 * ya no es el del campo) se descarta. Lo ya visto sale de una caché de la visita.
 */
export function NavbarSearch() {
  const t = useTranslations("nav.search");
  const contenido = useTranslations("common.content");
  const persona = useTranslations("search.person");
  const idioma = useLocale();
  const router = useRouter();
  const base = useId();
  const buscadorId = `${base}-buscador`;
  const listaId = `${base}-lista`;
  const encabezadoPersonas = `${base}-personas`;
  const encabezadoTitulos = `${base}-titulos`;

  const [abierto, setAbierto] = useState(false);
  const [texto, setTexto] = useState("");
  const [listaAbierta, setListaAbierta] = useState(false);
  const [sugerencias, setSugerencias] = useState<Sugerencia[] | null>(null);
  const [cargando, setCargando] = useState(false);
  const [activoId, setActivoId] = useState<string | null>(null);
  const [anuncio, setAnuncio] = useState("");

  const boton = useRef<HTMLButtonElement>(null);
  const campo = useRef<HTMLInputElement>(null);
  const contenedor = useRef<HTMLElement>(null);
  // Esc y ✕ devuelven el foco a la lupa; perder el foco no (queda donde el usuario lo puso).
  const volverALaLupa = useRef(false);

  const recortado = texto.trim();
  const sugiere = recortado.length >= MIN_CARACTERES;

  // Al desplegar, el foco va al campo; al plegar por teclado, vuelve a la lupa.
  useEffect(() => {
    if (abierto) campo.current?.focus();
    else if (volverALaLupa.current) {
      volverALaLupa.current = false;
      boton.current?.focus();
    }
  }, [abierto]);

  // «/» despliega la lupa y enfoca el campo, salvo que se esté escribiendo en otro.
  useEffect(() => {
    function alApretar(evento: globalThis.KeyboardEvent) {
      if (!esAtajoDeBusqueda(evento)) return;
      evento.preventDefault();
      if (abierto) campo.current?.focus();
      else setAbierto(true);
    }
    document.addEventListener("keydown", alApretar);
    return () => document.removeEventListener("keydown", alApretar);
  }, [abierto]);

  // Pide las sugerencias del texto. El `return` cancela el pedido y la espera
  // del texto anterior: ese es el «descartar lo viejo».
  useEffect(() => {
    if (!abierto) return;
    if (!sugiere) {
      setSugerencias(null);
      setCargando(false);
      return;
    }
    const guardadas = sugerenciasEnCache(idioma, recortado);
    if (guardadas) {
      setSugerencias(guardadas);
      setCargando(false);
      setAnuncio(t("count", { count: guardadas.length }));
      return;
    }
    const control = new AbortController();
    setCargando(true);
    const espera = window.setTimeout(() => {
      pedirSugerencias(recortado, idioma, control.signal).then(
        (lista) => {
          if (control.signal.aborted) return;
          setSugerencias(lista);
          setCargando(false);
          setAnuncio(t("count", { count: lista.length }));
        },
        () => {
          // 429 (Too Many Requests), 503 (Service Unavailable)…: la lista se cierra
          // sin avisar; Enter sigue llevando a Buscar, que muestra su propio error.
          if (control.signal.aborted) return;
          setSugerencias(null);
          setCargando(false);
        }
      );
    }, ESPERA_SUGERENCIAS_MS);
    return () => {
      window.clearTimeout(espera);
      control.abort();
    };
    // `t` cambia en cada render y solo se usa para el aviso.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierto, sugiere, recortado, idioma]);

  const visible = abierto && listaAbierta && sugiere && sugerencias !== null;
  const personas = (sugerencias ?? []).filter((s): s is SugerenciaPersona => s.tipo === "person");
  const titulos = (sugerencias ?? []).filter((s): s is SugerenciaTitulo => s.tipo !== "person");
  const filas: Fila[] = [
    ...[...personas, ...titulos].map((sugerencia) => ({ id: idDe(sugerencia), sugerencia })),
    { id: ID_VER_TODO, sugerencia: null },
  ];
  const activa = visible ? filas.find((fila) => fila.id === activoId) : undefined;

  function cerrarCampo(volverALupa: boolean) {
    volverALaLupa.current = volverALupa;
    setAbierto(false);
    setTexto("");
    setSugerencias(null);
    setCargando(false);
    setListaAbierta(false);
    setActivoId(null);
  }

  function cerrarLista() {
    setListaAbierta(false);
    setActivoId(null);
  }

  /** Va al destino de la fila y deja la lupa cerrada y vacía. */
  function ir(fila: Fila) {
    const { sugerencia } = fila;
    if (sugerencia === null) router.push(urlDeTexto(recortado));
    else if (sugerencia.tipo === "person") router.push(urlDePersona(sugerencia.id, sugerencia.rol));
    else router.push(routes.title(sugerencia.tipo, sugerencia.id));
    cerrarCampo(false);
  }

  function mover(paso: 1 | -1) {
    const actual = filas.findIndex((fila) => fila.id === activoId);
    let siguiente = actual + paso;
    // Pasada la última (o antes de la primera) se vuelve al campo: ninguna activa.
    if (actual === -1 && paso === -1) siguiente = filas.length - 1;
    setActivoId(siguiente < 0 || siguiente >= filas.length ? null : filas[siguiente].id);
  }

  function alApretar(evento: KeyboardEvent<HTMLInputElement>) {
    switch (evento.key) {
      case "ArrowDown":
        evento.preventDefault();
        if (!visible) {
          // Con la lista cerrada, ↓ (o Alt+↓) la vuelve a abrir con la última respuesta.
          if (sugiere && sugerencias !== null) setListaAbierta(true);
        } else if (!evento.altKey) mover(1);
        return;
      case "ArrowUp":
        if (!visible) return;
        evento.preventDefault();
        mover(-1);
        return;
      case "Enter":
        evento.preventDefault();
        if (activa) ir(activa);
        else if (recortado) ir({ id: ID_VER_TODO, sugerencia: null });
        return;
      case "Escape":
        // Que no cierre también lo que haya detrás (un diálogo, por ejemplo).
        evento.preventDefault();
        evento.stopPropagation();
        if (visible) cerrarLista();
        else cerrarCampo(true);
        return;
      case "Tab":
        // Tab deja el campo sin elegir nada.
        cerrarLista();
        return;
    }
  }

  function alSalirElFoco(evento: FocusEvent<HTMLElement>) {
    // Pasar el foco a la ✕ (dentro del mismo contenedor) no es salir.
    if (contenedor.current?.contains(evento.relatedTarget as Node | null)) return;
    cerrarLista();
    if (!recortado) setAbierto(false);
  }

  const etiquetaRol = (s: SugerenciaPersona) => persona("role", { role: s.rol, gender: s.genero });
  const etiquetaTitulo = (s: SugerenciaTitulo) =>
    t("titleMeta", {
      type: s.tipo === "movie" ? contenido("movie") : contenido("tvShow"),
      year: s.anio === null ? "none" : String(s.anio),
    });

  const opcion = (fila: Fila, contenidoDeLaFila: React.ReactNode, extra?: string) => (
    <div
      key={fila.id}
      id={fila.id}
      role="option"
      aria-selected={fila.id === activa?.id}
      // Sin robarle el foco al campo: el clic igual llega a `onClick`.
      onMouseDown={(evento) => evento.preventDefault()}
      onClick={() => ir(fila)}
      className={cn(
        "flex min-h-11 cursor-pointer items-center gap-3 rounded-lg px-2.5 py-1.5",
        fila.id === activa?.id && "bg-raised-2",
        extra
      )}
    >
      {contenidoDeLaFila}
    </div>
  );

  return (
    // Ocupa siempre el lugar de un botón (2,75 rem): desplegarse no mueve la barra.
    <div className="relative size-11 shrink-0 max-md:hidden">
      <button
        ref={boton}
        type="button"
        aria-expanded={abierto}
        aria-controls={abierto ? buscadorId : undefined}
        aria-keyshortcuts="/"
        aria-label={t("openLabel")}
        title={t("openLabel")}
        onClick={() => setAbierto(true)}
        className={cn(
          "grid size-11 cursor-pointer place-items-center rounded-[0.625rem] text-fg-2 hover:bg-raised-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
          // Desplegado, el campo se pone encima: la lupa se esconde pero sigue en el DOM.
          abierto && "invisible"
        )}
      >
        <Search aria-hidden="true" className="size-5" />
      </button>
      {abierto && (
        <search
          id={buscadorId}
          ref={contenedor}
          aria-label={t("label")}
          onBlur={alSalirElFoco}
          // Crece hacia la izquierda desde el lugar de la lupa; sin animación
          // si el sistema pide menos movimiento.
          className="absolute top-0 right-0 z-40 w-80 motion-safe:animate-[desplegar-busqueda_180ms_ease-out]"
        >
          <div className="flex h-11 items-center gap-2 rounded-[0.625rem] bg-raised pr-1 pl-3 shadow-[inset_0_0_0_1px_var(--field-border)] focus-within:shadow-[inset_0_0_0_2px_var(--ring)]">
            <Search aria-hidden="true" className="size-[1.125rem] shrink-0 text-fg-3" />
            <label htmlFor={`${base}-campo`} className="sr-only">
              {t("label")}
            </label>
            <input
              ref={campo}
              id={`${base}-campo`}
              type="text"
              role="combobox"
              autoComplete="off"
              maxLength={MAX_TEXTO}
              aria-autocomplete="list"
              aria-expanded={visible}
              aria-controls={listaId}
              aria-activedescendant={activa?.id}
              value={texto}
              placeholder={t("placeholder")}
              onChange={(evento) => {
                setTexto(evento.target.value);
                setListaAbierta(true);
              }}
              onFocus={() => setListaAbierta(true)}
              onKeyDown={alApretar}
              className="h-full min-w-0 flex-1 border-0 bg-transparent text-[0.9375rem] text-foreground outline-none placeholder:text-fg-3"
            />
            {!texto && (
              <kbd
                aria-hidden="true"
                className="rounded-md px-1.5 py-0.5 font-sans text-xs font-semibold text-fg-3 shadow-[inset_0_0_0_1px_var(--line)]"
              >
                /
              </kbd>
            )}
            <button
              type="button"
              aria-label={t("closeLabel")}
              onClick={() => cerrarCampo(true)}
              className="grid size-9 shrink-0 cursor-pointer place-items-center rounded-lg text-fg-3 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
            >
              <X aria-hidden="true" className="size-[1.125rem]" />
            </button>
          </div>
          {visible && (
            <div
              id={listaId}
              role="listbox"
              aria-label={t("label")}
              aria-busy={cargando}
              className="absolute top-full right-0 mt-2 w-[22.5rem] rounded-xl bg-raised p-1.5 shadow-[inset_0_0_0_1px_var(--line),0_16px_40px_rgb(0_0_0/0.45)]"
            >
              {personas.length > 0 && (
                <div role="group" aria-labelledby={encabezadoPersonas}>
                  <div
                    id={encabezadoPersonas}
                    className="px-2.5 pt-2 pb-1 text-[0.6875rem] font-semibold tracking-[0.08em] text-fg-3 uppercase"
                  >
                    {t("groupPeople")}
                  </div>
                  {personas.map((s) =>
                    opcion(
                      { id: idDe(s), sugerencia: s },
                      <>
                        {s.foto ? (
                          <Image
                            src={s.foto}
                            alt=""
                            width={34}
                            height={34}
                            loader={tmdbLoader}
                            className="size-[2.125rem] shrink-0 rounded-full object-cover"
                          />
                        ) : (
                          <span
                            aria-hidden="true"
                            className="grid size-[2.125rem] shrink-0 place-items-center rounded-full bg-raised-2 text-sm font-semibold text-fg-2"
                          >
                            {s.nombre.charAt(0)}
                          </span>
                        )}
                        <span className="min-w-0">
                          <span className="block truncate font-medium">{s.nombre}</span>
                          <span className="block text-xs text-fg-3">{etiquetaRol(s)}</span>
                        </span>
                      </>
                    )
                  )}
                </div>
              )}
              {titulos.length > 0 && (
                <div role="group" aria-labelledby={encabezadoTitulos}>
                  <div
                    id={encabezadoTitulos}
                    className="px-2.5 pt-2 pb-1 text-[0.6875rem] font-semibold tracking-[0.08em] text-fg-3 uppercase"
                  >
                    {t("groupTitles")}
                  </div>
                  {titulos.map((s) =>
                    opcion(
                      { id: idDe(s), sugerencia: s },
                      <>
                        {s.poster ? (
                          <Image
                            src={s.poster}
                            alt=""
                            width={28}
                            height={40}
                            loader={tmdbLoader}
                            className="h-10 w-7 shrink-0 rounded object-cover"
                          />
                        ) : (
                          <span
                            aria-hidden="true"
                            className="h-10 w-7 shrink-0 rounded bg-raised-2"
                          />
                        )}
                        <span className="min-w-0">
                          <span className="block truncate font-medium">{s.titulo}</span>
                          <span className="block text-xs text-fg-3">{etiquetaTitulo(s)}</span>
                        </span>
                      </>
                    )
                  )}
                </div>
              )}
              {opcion(
                { id: ID_VER_TODO, sugerencia: null },
                <>
                  <span className="min-w-0 flex-1 truncate font-semibold text-primary">
                    {t("seeAll", { query: recortado })}
                  </span>
                  <CornerDownLeft aria-hidden="true" className="size-4 shrink-0 text-fg-3" />
                </>,
                "mt-1 border-t border-line rounded-t-none pt-2"
              )}
            </div>
          )}
          <div role="status" className="sr-only">
            {anuncio}
          </div>
        </search>
      )}
    </div>
  );
}
