"use client";

import { Check, ChevronDown, Search } from "lucide-react";
import {
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { useLocale, useTranslations } from "next-intl";

import { FieldMessage, fieldClass } from "@/components/access/fields";
import type { AppLocale } from "@/i18n/config";
import { paisesOrdenados } from "@/lib/format";
import { cn } from "@/lib/utils";

type Props = {
  value: string;
  onChange: (code: string) => void;
  /** Al cerrar la lista después de haberla abierto; pasar por el campo con Tab no cuenta. */
  onBlur?: () => void;
  /** Mensaje ya traducido; `FieldError` lo anuncia. */
  error?: string | null;
  id?: string;
  name?: string;
  autoFocus?: boolean;
  required?: boolean;
  className?: string;
  /** Clases del botón que muestra el país (el «campo»). */
  selectClassName?: string;
  labelClassName?: string;
  /** Guarda un renglón para el error aunque no lo haya (sin saltos de layout). */
  reserveMessage?: boolean;
};

/** Margen entre el campo y la lista, y entre la lista y el borde de la ventana. */
const MARGEN_PX = 8;

/** Sin tildes ni mayúsculas: «peru» encuentra «Perú». */
function normalizar(texto: string) {
  return texto
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

/**
 * Selector de país compartido por el registro, el alta con Google y el perfil.
 *
 * Reemplaza al `<select>` nativo (06/11/2026): con unos 250 países, el
 * navegador decidía dónde abrir la lista y la estiraba hasta el borde de la
 * ventana. Esta lista se abre debajo del campo, con alto fijo (8 países a la
 * vista) y un buscador. Si abajo no entra, la página baja lo que falta; solo
 * se abre hacia arriba cuando la página ya no puede bajar más.
 *
 * Accesibilidad (patrón «combobox» de la APG): el botón es el `combobox` y
 * anuncia el país elegido; el buscador maneja la opción activa con
 * `aria-activedescendant`. Flechas para moverse, Enter elige, Escape cierra y
 * devuelve el foco al campo; Tab o un clic afuera cierran sin elegir.
 *
 * Arranca vacío, sin adivinar por el navegador: el usuario tiene que elegir.
 * Los nombres salen de `Intl.DisplayNames`, ordenados en el idioma activo.
 */
export function CountrySelect({
  value,
  onChange,
  onBlur,
  error,
  id,
  name = "pais",
  autoFocus,
  required,
  className,
  selectClassName,
  labelClassName,
  reserveMessage = false,
}: Props) {
  const t = useTranslations("common");
  const locale = useLocale() as AppLocale;
  const generated = useId();
  const fieldId = id ?? generated;
  const listId = `${fieldId}-lista`;
  const errorId = `${fieldId}-error`;
  const paises = useMemo(() => paisesOrdenados(locale), [locale]);

  const [abierto, setAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [activo, setActivo] = useState(0);
  const [haciaArriba, setHaciaArriba] = useState(false);
  // Píxeles que se le quitan a la lista si no entra entera en ningún lado.
  const [recorte, setRecorte] = useState(0);

  const contenedor = useRef<HTMLDivElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const buscador = useRef<HTMLInputElement>(null);
  const lista = useRef<HTMLUListElement>(null);

  const filtrados = useMemo(() => {
    const consulta = normalizar(busqueda.trim());
    return consulta ? paises.filter((pais) => normalizar(pais.name).includes(consulta)) : paises;
  }, [busqueda, paises]);
  const elegido = paises.find((pais) => pais.code === value);
  const opcionId = (code: string) => `${fieldId}-opcion-${code}`;
  const activa = filtrados[activo];

  function abrir(texto = "") {
    setBusqueda(texto);
    const indice = texto ? 0 : paises.findIndex((pais) => pais.code === value);
    setActivo(Math.max(indice, 0));
    setRecorte(0);
    setAbierto(true);
  }

  function cerrar(volverAlCampo: boolean) {
    setAbierto(false);
    setBusqueda("");
    onBlur?.();
    if (volverAlCampo) boton.current?.focus();
  }

  function elegir(code: string) {
    onChange(code);
    cerrar(true);
  }

  // Antes de pintar: medir y decidir si la lista va abajo o arriba del campo.
  useLayoutEffect(() => {
    if (!abierto || !boton.current || !panel.current) return;
    const campo = boton.current.getBoundingClientRect();
    const alto = panel.current.offsetHeight;
    const abajo = window.innerHeight - campo.bottom - MARGEN_PX * 2;
    const encima = campo.top - MARGEN_PX * 2;
    // Siempre debajo del campo: si no entra, la página baja lo que falta.
    // Solo se abre hacia arriba cuando la página ya no puede bajar más.
    const falta = alto - abajo;
    const scrollRestante =
      document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
    let arriba = false;
    if (falta > 0 && scrollRestante >= falta) {
      window.scrollBy({ top: falta, behavior: "smooth" });
    } else if (falta > 0) {
      arriba = encima > abajo + scrollRestante;
    }
    const disponible = arriba ? encima : abajo + Math.max(scrollRestante, 0);
    setHaciaArriba(arriba);
    setRecorte(Math.max(0, alto - disponible));
    buscador.current?.focus({ preventScroll: true });
  }, [abierto]);

  // La opción activa siempre a la vista (al abrir, la elegida). Se mueve solo
  // la lista: `scrollIntoView` movería también la página y cortaría el scroll
  // que hace lugar debajo del campo.
  useEffect(() => {
    const ul = lista.current;
    const li = activa ? document.getElementById(opcionId(activa.code)) : null;
    if (!abierto || !ul || !li) return;
    if (li.offsetTop < ul.scrollTop) ul.scrollTop = li.offsetTop;
    else if (li.offsetTop + li.offsetHeight > ul.scrollTop + ul.clientHeight)
      ul.scrollTop = li.offsetTop + li.offsetHeight - ul.clientHeight;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `opcionId` solo depende de `fieldId`.
  }, [abierto, activa]);

  // Un clic o un toque fuera del componente cierra sin elegir.
  useEffect(() => {
    if (!abierto) return;
    const alTocar = (evento: PointerEvent) => {
      if (!contenedor.current?.contains(evento.target as Node)) cerrar(false);
    };
    document.addEventListener("pointerdown", alTocar);
    return () => document.removeEventListener("pointerdown", alTocar);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `cerrar` cambia en cada render.
  }, [abierto]);

  function teclaEnCampo(evento: KeyboardEvent<HTMLButtonElement>) {
    if (abierto) return;
    if (evento.key === "ArrowDown" || evento.key === "ArrowUp") {
      evento.preventDefault();
      abrir();
    } else if (
      evento.key.length === 1 &&
      evento.key !== " " &&
      !evento.ctrlKey &&
      !evento.metaKey &&
      !evento.altKey
    ) {
      // Escribir sobre el campo cerrado abre la lista y empieza a buscar.
      evento.preventDefault();
      abrir(evento.key);
    }
  }

  function teclaEnBuscador(evento: KeyboardEvent<HTMLInputElement>) {
    const mover = (paso: number) => {
      evento.preventDefault();
      setActivo((actual) => Math.min(Math.max(actual + paso, 0), filtrados.length - 1));
    };
    switch (evento.key) {
      case "ArrowDown":
        return mover(1);
      case "ArrowUp":
        return mover(-1);
      case "PageDown":
        return mover(8);
      case "PageUp":
        return mover(-8);
      case "Enter":
        evento.preventDefault();
        if (activa) elegir(activa.code);
        return;
      case "Escape":
        // Que no cierre también un diálogo o la búsqueda que contenga al campo.
        evento.preventDefault();
        evento.stopPropagation();
        cerrar(true);
        return;
      case "Tab":
        cerrar(false);
        return;
    }
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <label htmlFor={fieldId} className={cn("text-sm font-semibold", labelClassName)}>
        {t("fields.country")}
      </label>
      <div ref={contenedor} className="relative">
        <button
          ref={boton}
          id={fieldId}
          type="button"
          role="combobox"
          autoFocus={autoFocus}
          aria-haspopup="listbox"
          aria-expanded={abierto}
          aria-controls={abierto ? listId : undefined}
          aria-required={required ? true : undefined}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          onClick={() => (abierto ? cerrar(true) : abrir())}
          onKeyDown={teclaEnCampo}
          className={cn(
            fieldClass,
            "flex cursor-pointer items-center justify-between gap-2 text-left",
            selectClassName
          )}
        >
          <span className={cn("truncate", !elegido && "text-fg-3")}>
            {elegido ? elegido.name : t("country.placeholder")}
          </span>
          <ChevronDown
            aria-hidden="true"
            className={cn(
              "size-5 flex-none text-fg-3 transition-transform",
              abierto && "rotate-180"
            )}
          />
        </button>
        <input type="hidden" name={name} value={value} />
        {abierto && (
          <div
            ref={panel}
            className={cn(
              "absolute inset-x-0 z-40 flex flex-col gap-1.5 rounded-[0.625rem] bg-raised p-1.5 shadow-[inset_0_0_0_1px_var(--line),0_16px_40px_rgb(0_0_0/0.45)]",
              haciaArriba ? "bottom-full mb-2" : "top-full mt-2"
            )}
          >
            <div className="relative">
              <Search
                aria-hidden="true"
                className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-fg-3"
              />
              <input
                ref={buscador}
                type="search"
                autoComplete="off"
                aria-label={t("country.searchLabel")}
                aria-controls={listId}
                aria-activedescendant={activa ? opcionId(activa.code) : undefined}
                value={busqueda}
                onChange={(evento) => {
                  setBusqueda(evento.target.value);
                  setActivo(0);
                }}
                onKeyDown={teclaEnBuscador}
                className="h-11 w-full rounded-lg border-0 bg-card pr-3 pl-9 text-base text-foreground shadow-[inset_0_0_0_1px_var(--field-border)] placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-ring"
                placeholder={t("country.searchLabel")}
              />
            </div>
            <ul
              ref={lista}
              id={listId}
              role="listbox"
              aria-label={t("fields.country")}
              // 8 opciones de 2.75rem; menos solo si no entra en la ventana.
              style={{ maxHeight: `max(8.25rem, calc(22rem - ${recorte}px))` }}
              className="relative overflow-y-auto overscroll-contain"
            >
              {filtrados.map((pais, indice) => {
                const marcado = pais.code === value;
                return (
                  <li
                    key={pais.code}
                    id={opcionId(pais.code)}
                    role="option"
                    aria-selected={marcado}
                    // Sin robarle el foco al buscador.
                    onPointerDown={(evento) => evento.preventDefault()}
                    onClick={() => elegir(pais.code)}
                    onPointerMove={() => setActivo(indice)}
                    className={cn(
                      "flex h-11 cursor-pointer items-center justify-between gap-2 rounded-lg px-3",
                      indice === activo && "bg-raised-2",
                      marcado && "font-semibold"
                    )}
                  >
                    <span className="truncate">{pais.name}</span>
                    {marcado && (
                      <Check aria-hidden="true" className="size-4 flex-none text-primary" />
                    )}
                  </li>
                );
              })}
            </ul>
            {filtrados.length === 0 && (
              <p role="status" className="px-3 py-3 text-sm text-fg-3">
                {t("country.noResults")}
              </p>
            )}
          </div>
        )}
      </div>
      <FieldMessage id={errorId} error={error} reserve={reserveMessage} />
    </div>
  );
}
