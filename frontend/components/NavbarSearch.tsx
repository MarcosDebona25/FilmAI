"use client";

import { useEffect, useId, useRef, useState, type FocusEvent, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { Search, X } from "lucide-react";
import { useTranslations } from "next-intl";

import { SugerenciasLista } from "@/components/SugerenciasLista";
import { routes } from "@/lib/routes";
import { MAX_TEXTO, urlDePersona, urlDeTexto } from "@/lib/search";
import {
  ID_VER_TODO,
  esAtajoDeBusqueda,
  filasDeSugerencias,
  moverActiva,
  type Fila,
} from "@/lib/sugerencias";
import { useSugerencias } from "@/lib/use-sugerencias";
import { cn } from "@/lib/utils";

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
  const router = useRouter();
  const base = useId();
  const buscadorId = `${base}-buscador`;
  const listaId = `${base}-lista`;

  const [abierto, setAbierto] = useState(false);
  const [texto, setTexto] = useState("");
  const [listaAbierta, setListaAbierta] = useState(false);
  const [activoId, setActivoId] = useState<string | null>(null);

  const boton = useRef<HTMLButtonElement>(null);
  const campo = useRef<HTMLInputElement>(null);
  const contenedor = useRef<HTMLElement>(null);
  // Esc y ✕ devuelven el foco a la lupa; perder el foco no (queda donde el usuario lo puso).
  const volverALaLupa = useRef(false);

  const recortado = texto.trim();
  // El pedido (250 ms, 2 caracteres, cancelación, caché) vive en el hook, que
  // comparte con el campo de Buscar.
  const { sugiere, sugerencias, cargando, anuncio, descartar } = useSugerencias(texto, abierto);

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
      // Por debajo de 768 px la lupa está oculta (`max-md:hidden`) pero montada:
      // sin este corte, «/» se comería la tecla y abriría un campo invisible.
      if (!window.matchMedia("(min-width: 48rem)").matches) return;
      evento.preventDefault();
      if (abierto) campo.current?.focus();
      else setAbierto(true);
    }
    document.addEventListener("keydown", alApretar);
    return () => document.removeEventListener("keydown", alApretar);
  }, [abierto]);

  const visible = abierto && listaAbierta && sugiere && sugerencias !== null;
  const filas = filasDeSugerencias(sugerencias ?? [], true);
  const activa = visible ? filas.find((fila) => fila.id === activoId) : undefined;

  function cerrarCampo(volverALupa: boolean) {
    volverALaLupa.current = volverALupa;
    setAbierto(false);
    setTexto("");
    descartar();
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
    setActivoId(moverActiva(filas, activoId, paso));
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
          "grid size-11 cursor-pointer place-items-center rounded-full text-fg-2 hover:bg-raised-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
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
          // si el sistema pide menos movimiento. El ancho acompaña a la pantalla:
          // 20rem a 1440 px, unos 15,4rem a 1024 px y 12rem a 768 px.
          className="absolute top-0 right-0 z-40 w-[clamp(12rem,24vw,20rem)] motion-safe:animate-[desplegar-busqueda_180ms_ease-out]"
        >
          {/* Píldora del canvas (sección 13): con foco, borde `--fg-3` y un anillo de 2 px por fuera. */}
          <div className="flex h-11 items-center rounded-full bg-raised pr-0.5 pl-3.5 shadow-[inset_0_0_0_1px_var(--field-border)] focus-within:shadow-[inset_0_0_0_1px_var(--fg-3),0_0_0_2px_var(--ring)]">
            <Search aria-hidden="true" className="mr-2.5 size-5 shrink-0 text-fg-3" />
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
              className="h-full min-w-0 flex-1 border-0 bg-transparent pr-1 text-[0.9375rem] font-medium text-foreground outline-none placeholder:text-fg-3"
            />
            {!texto && (
              <kbd
                aria-hidden="true"
                className="mr-1.5 rounded-md px-1.5 py-0.5 font-sans text-xs font-semibold text-fg-3 shadow-[inset_0_0_0_1px_var(--line)]"
              >
                /
              </kbd>
            )}
            <button
              type="button"
              aria-label={t("closeLabel")}
              onClick={() => cerrarCampo(true)}
              className="grid size-10 shrink-0 cursor-pointer place-items-center rounded-full text-fg-3 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              <X aria-hidden="true" className="size-[1.125rem]" />
            </button>
          </div>
          {visible && (
            <SugerenciasLista
              id={listaId}
              sugerencias={sugerencias ?? []}
              cargando={cargando}
              activaId={activa?.id}
              alElegir={ir}
              verTodo={recortado}
              rica
              className="absolute top-full right-0 mt-2 w-[26rem]"
            />
          )}
          <div role="status" className="sr-only">
            {anuncio}
          </div>
        </search>
      )}
    </div>
  );
}
