"use client";

import { useId, type ReactNode } from "react";
import Image from "next/image";
import { ArrowRight, CornerDownLeft } from "lucide-react";
import { useTranslations } from "next-intl";

import { StarIcon } from "@/components/ui/StarIcon";
import { tmdbLoader } from "@/lib/catalog";
import { useFormats } from "@/lib/format";
import {
  ID_VER_TODO,
  agruparSugerencias,
  idDe,
  inicialesDe,
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
  /**
   * El desplegable «rico» de la lupa de la navbar (canvas, sección 13): filas de
   * 84 px, póster de 48 × 72, nota de TMDB y fotos de 48 px. Sin él queda la
   * lista compacta del campo de Buscar.
   */
  rica?: boolean;
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
  rica = false,
  className,
}: Props) {
  const t = useTranslations("nav.search");
  const contenido = useTranslations("common.content");
  const persona = useTranslations("search.person");
  const media = useTranslations("common.media");
  const formats = useFormats();
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
        "flex cursor-pointer items-center",
        rica
          ? "min-h-21 gap-3.5 rounded-[0.625rem] px-2.5 py-1"
          : "min-h-11 gap-3 rounded-lg px-2.5 py-1.5",
        fila.id === activaId && "bg-raised-2",
        extra
      )}
    >
      {contenidoDeLaFila}
    </div>
  );

  const encabezado =
    "px-2.5 pt-2 pb-1 text-[0.6875rem] font-semibold tracking-[0.08em] text-fg-3 uppercase";
  // Las dos líneas de texto de una fila: nombre o título arriba, el dato abajo.
  const textos = rica ? "flex min-w-0 flex-col gap-[0.1875rem]" : "min-w-0";
  const principal = rica
    ? "truncate text-base leading-tight font-semibold"
    : "block truncate font-medium";
  const secundario = rica ? "text-[0.8125rem] text-fg-3" : "block text-xs text-fg-3";
  const foto = rica ? { lado: 48, clase: "size-12" } : { lado: 34, clase: "size-[2.125rem]" };
  const poster = rica
    ? { ancho: 48, alto: 72, clase: "h-18 w-12 rounded-md" }
    : { ancho: 28, alto: 40, clase: "h-10 w-7 rounded" };

  return (
    <div
      id={id}
      role="listbox"
      aria-label={t("label")}
      aria-busy={cargando}
      className={cn(
        "bg-raised p-1.5",
        rica
          ? "rounded-[0.875rem] shadow-[inset_0_0_0_1px_var(--line),0_16px_40px_rgb(0_0_0/0.5)]"
          : "rounded-xl shadow-[inset_0_0_0_1px_var(--line),0_16px_40px_rgb(0_0_0/0.45)]",
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
                    width={foto.lado}
                    height={foto.lado}
                    loader={tmdbLoader}
                    className={cn("shrink-0 rounded-full object-cover", foto.clase)}
                  />
                ) : (
                  <span
                    aria-hidden="true"
                    className={cn(
                      "grid shrink-0 place-items-center rounded-full bg-raised-2 text-sm text-fg-2",
                      foto.clase,
                      rica ? "font-bold" : "font-semibold"
                    )}
                  >
                    {inicialesDe(s.nombre)}
                  </span>
                )}
                <span className={textos}>
                  <span className={principal}>{s.nombre}</span>
                  <span className={secundario}>{etiquetaRol(s)}</span>
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
                    width={poster.ancho}
                    height={poster.alto}
                    loader={tmdbLoader}
                    className={cn("shrink-0 bg-raised-2 object-cover", poster.clase)}
                  />
                ) : (
                  <span aria-hidden="true" className={cn("shrink-0 bg-raised-2", poster.clase)} />
                )}
                <span className={textos}>
                  <span className={principal}>{s.titulo}</span>
                  <span className={cn(secundario, rica && "inline-flex items-center gap-2")}>
                    {etiquetaTitulo(s)}
                    {rica && s.nota !== null && (
                      <span className="inline-flex items-center gap-1 text-fg-2">
                        <span className="sr-only">
                          {media("tmdbRatingLabel", { rating: formats.rating(s.nota) })}
                        </span>
                        <StarIcon className="size-3 fill-primary" />
                        <span aria-hidden="true">{formats.rating(s.nota)}</span>
                      </span>
                    )}
                  </span>
                </span>
              </>
            )
          )}
        </div>
      )}
      {verTodo !== undefined &&
        opcion(
          { id: ID_VER_TODO, sugerencia: null },
          rica ? (
            <>
              <span className="min-w-0 flex-1 truncate">{t("seeAll", { query: verTodo })}</span>
              <ArrowRight aria-hidden="true" className="size-[1.125rem] shrink-0" />
            </>
          ) : (
            <>
              <span className="min-w-0 flex-1 truncate font-semibold text-primary">
                {t("seeAll", { query: verTodo })}
              </span>
              <CornerDownLeft aria-hidden="true" className="size-4 shrink-0 text-fg-3" />
            </>
          ),
          rica
            ? "mt-1 min-h-12 gap-2 py-0 text-sm font-semibold text-fg-2 shadow-[inset_0_1px_0_var(--line)]"
            : "mt-1 rounded-t-none border-t border-line pt-2"
        )}
    </div>
  );
}
