"use client";

import { useId, type ReactNode } from "react";
import Image from "next/image";
import { CornerDownLeft } from "lucide-react";
import { useTranslations } from "next-intl";

import { tmdbLoader } from "@/lib/catalog";
import {
  ID_VER_TODO,
  agruparSugerencias,
  idDe,
  type Fila,
  type Sugerencia,
  type SugerenciaPersona,
  type SugerenciaTitulo,
} from "@/lib/sugerencias";
import { cn } from "@/lib/utils";

interface Props {
  /** Id del `role="listbox"`: el que apunta `aria-controls` del campo. */
  id: string;
  sugerencias: Sugerencia[];
  cargando: boolean;
  /** Id de la opción activa (`aria-selected`), o `undefined` si el foco está en el campo. */
  activaId: string | undefined;
  alElegir: (fila: Fila) => void;
  /** Texto de «Ver todos los resultados» para el final de la lista; sin él, no hay esa fila. */
  verTodo?: string;
  className?: string;
}

/**
 * La lista de sugerencias (el `listbox` del combobox): personas y títulos en
 * dos grupos. Solo dibuja: qué opción está activa y qué pasa al elegir lo
 * decide el componente que tiene el campo (la lupa de la navbar o Buscar).
 * Es el equivalente de una «vista parcial» que dos pantallas comparten.
 */
export function SugerenciasLista({
  id,
  sugerencias,
  cargando,
  activaId,
  alElegir,
  verTodo,
  className,
}: Props) {
  const t = useTranslations("nav.search");
  const contenido = useTranslations("common.content");
  const persona = useTranslations("search.person");
  const base = useId();
  const encabezadoPersonas = `${base}-personas`;
  const encabezadoTitulos = `${base}-titulos`;
  const { personas, titulos } = agruparSugerencias(sugerencias);

  const etiquetaRol = (s: SugerenciaPersona) => persona("role", { role: s.rol, gender: s.genero });
  const etiquetaTitulo = (s: SugerenciaTitulo) =>
    t("titleMeta", {
      type: s.tipo === "movie" ? contenido("movie") : contenido("tvShow"),
      year: s.anio === null ? "none" : String(s.anio),
    });

  const opcion = (fila: Fila, contenidoDeLaFila: ReactNode, extra?: string) => (
    <div
      key={fila.id}
      id={fila.id}
      role="option"
      aria-selected={fila.id === activaId}
      // Sin robarle el foco al campo: el clic igual llega a `onClick`.
      onMouseDown={(evento) => evento.preventDefault()}
      onClick={() => alElegir(fila)}
      className={cn(
        "flex min-h-11 cursor-pointer items-center gap-3 rounded-lg px-2.5 py-1.5",
        fila.id === activaId && "bg-raised-2",
        extra
      )}
    >
      {contenidoDeLaFila}
    </div>
  );

  const encabezado =
    "px-2.5 pt-2 pb-1 text-[0.6875rem] font-semibold tracking-[0.08em] text-fg-3 uppercase";

  return (
    <div
      id={id}
      role="listbox"
      aria-label={t("label")}
      aria-busy={cargando}
      className={cn(
        "rounded-xl bg-raised p-1.5 shadow-[inset_0_0_0_1px_var(--line),0_16px_40px_rgb(0_0_0/0.45)]",
        className
      )}
    >
      {personas.length > 0 && (
        <div role="group" aria-labelledby={encabezadoPersonas}>
          <div id={encabezadoPersonas} className={encabezado}>
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
          <div id={encabezadoTitulos} className={encabezado}>
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
                  <span aria-hidden="true" className="h-10 w-7 shrink-0 rounded bg-raised-2" />
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
      {verTodo !== undefined &&
        opcion(
          { id: ID_VER_TODO, sugerencia: null },
          <>
            <span className="min-w-0 flex-1 truncate font-semibold text-primary">
              {t("seeAll", { query: verTodo })}
            </span>
            <CornerDownLeft aria-hidden="true" className="size-4 shrink-0 text-fg-3" />
          </>,
          "mt-1 border-t border-line rounded-t-none pt-2"
        )}
    </div>
  );
}
