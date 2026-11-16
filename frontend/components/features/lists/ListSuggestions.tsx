"use client";

import { useEffect, useId, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { LoaderCircle, Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { mensajeDeError } from "@/components/features/title/RatingDialog";
import { StarIcon } from "@/components/ui/StarIcon";
import { apiFetch } from "@/lib/api";
import { tmdbImage, tmdbLoader } from "@/lib/catalog";
import { useFormats } from "@/lib/format";
import {
  claveDeSugerencia,
  type ItemLista,
  type PaginaSugerencias,
  type Sugerencia,
} from "@/lib/lists";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

type Datos = { entradas: Sugerencia[]; pagina: number; paginas: number; nombreUsado: boolean };

/**
 * «Suggested for this list» (canvas, sección 14): banda abierta al final del
 * detalle, sin caja, con una fila compacta por título y «+ Add».
 *
 * - No pide nada hasta ser `visible` por primera vez y después conserva lo que
 *   trajo: filtrar la grilla la oculta o la muestra, pero no la vuelve a pedir.
 * - «Show more suggestions» pide `?pagina=N+1` y agrega lo nuevo debajo; se
 *   oculta en la última página.
 * - `revision` cambia cuando la lista cambia (alta, baja, renombre). El backend
 *   arma entonces otro pool, con otro orden: el próximo «Show more» vuelve a la
 *   página 1 de ese pool y saltea lo que la banda ya mostró.
 */
export function ListSuggestions({
  listaId,
  nombre,
  cantidad,
  revision,
  visible,
  onAgregada,
  onAgotada,
}: {
  listaId: number;
  /** Nombre visible de la lista (el de Favorites y Watched ya viene traducido). */
  nombre: string;
  /** Títulos de la lista entera, para la frase «Based on its N titles». */
  cantidad: number;
  revision: number;
  visible: boolean;
  onAgregada: (item: ItemLista) => void;
  /**
   * Se agregó la última sugerencia y no hay más páginas: la banda deja de
   * dibujarse. El foco estaba en su «+ Add», así que lo reubica la pantalla.
   */
  onAgotada: () => void;
}) {
  const t = useTranslations();
  const formats = useFormats();
  const [datos, setDatos] = useState<Datos | null>(null);
  const [cargandoMas, setCargandoMas] = useState(false);
  const [agregando, setAgregando] = useState<string | null>(null);
  const [fallidos, setFallidos] = useState<string[]>([]);
  const pedida = useRef(false);
  const mostradas = useRef(new Set<string>());
  const revisionDelPool = useRef(revision);
  const seccion = useRef<HTMLElement>(null);
  const tituloId = useId();

  const pedir = (numero: number) =>
    apiFetch<PaginaSugerencias>(`/api/lists/${listaId}/suggestions/?pagina=${numero}`);

  useEffect(() => {
    if (!visible || pedida.current) return;
    pedida.current = true;
    revisionDelPool.current = revision;
    pedir(1).then(
      (pagina) => {
        for (const sugerencia of pagina.results)
          mostradas.current.add(claveDeSugerencia(sugerencia));
        setDatos({
          entradas: pagina.results,
          pagina: pagina.pagina,
          paginas: pagina.paginas,
          nombreUsado: pagina.nombre_usado,
        });
      },
      // Es un agregado de la pantalla: si falla, la lista sigue igual y la
      // banda no se dibuja (el canvas no trae un estado de error).
      () => undefined
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps -- se pide una sola vez, al hacerse visible
  }, [visible]);

  /** Después de que React pinte: el foco va a lo que quedó en lugar de lo que se fue. */
  function enfocar(selector: string) {
    requestAnimationFrame(() => {
      const candidatos = [...(seccion.current?.querySelectorAll<HTMLElement>(selector) ?? [])];
      // «Show more» está dos veces (escritorio y celular): se elige el que se ve.
      (candidatos.find((nodo) => nodo.offsetParent !== null) ?? candidatos[0])?.focus();
    });
  }

  async function verMas() {
    if (!datos || cargandoMas) return;
    const revisionPedida = revision;
    let numero = revisionPedida === revisionDelPool.current ? datos.pagina + 1 : 1;
    setCargandoMas(true);
    try {
      let pagina = await pedir(numero);
      let nuevas = pagina.results.filter((s) => !mostradas.current.has(claveDeSugerencia(s)));
      // Con un pool nuevo, una página puede traer solo títulos ya mostrados:
      // se sigue hasta encontrar algo o llegar a la última.
      while (nuevas.length === 0 && pagina.pagina < pagina.paginas) {
        numero = pagina.pagina + 1;
        pagina = await pedir(numero);
        nuevas = pagina.results.filter((s) => !mostradas.current.has(claveDeSugerencia(s)));
      }
      revisionDelPool.current = revisionPedida;
      for (const sugerencia of nuevas) mostradas.current.add(claveDeSugerencia(sugerencia));
      setDatos((actual) =>
        actual
          ? {
              entradas: [...actual.entradas, ...nuevas],
              pagina: pagina.pagina,
              paginas: pagina.paginas,
              nombreUsado: pagina.nombre_usado,
            }
          : actual
      );
      // En la última página el botón se va y se llevaría el foco.
      if (pagina.pagina >= pagina.paginas)
        enfocar(
          nuevas.length ? `[data-sugerencia="${claveDeSugerencia(nuevas[0])}"] [data-titulo]` : "h2"
        );
    } catch (motivo) {
      toast.error(mensajeDeError(motivo));
    } finally {
      setCargandoMas(false);
    }
  }

  async function agregar(sugerencia: Sugerencia) {
    if (!datos || agregando) return;
    const clave = claveDeSugerencia(sugerencia);
    setAgregando(clave);
    try {
      const item = await apiFetch<ItemLista>(`/api/lists/${listaId}/items/`, {
        method: "POST",
        body: { id_tmdb: sugerencia.id_tmdb, tipo: sugerencia.tipo },
      });
      const indice = datos.entradas.findIndex((otra) => claveDeSugerencia(otra) === clave);
      const quedan = datos.entradas.filter((otra) => claveDeSugerencia(otra) !== clave);
      // El título ya es de la lista: sale de las sugerencias (canvas).
      setDatos((actual) =>
        actual
          ? {
              ...actual,
              entradas: actual.entradas.filter((otra) => claveDeSugerencia(otra) !== clave),
            }
          : actual
      );
      onAgregada(item);
      const vecina = quedan[Math.min(indice, quedan.length - 1)];
      if (vecina) enfocar(`[data-sugerencia="${claveDeSugerencia(vecina)}"] [data-agregar]`);
      else if (datos.pagina < datos.paginas) enfocar("[data-ver-mas]");
      // Sin sugerencias ni «Show more» la banda desaparece entera: adentro no
      // queda dónde dejar el foco y, sin avisar, caería en <body>.
      else onAgotada();
    } catch (motivo) {
      toast.error(mensajeDeError(motivo));
    } finally {
      setAgregando(null);
    }
  }

  if (!visible || !datos) return null;
  const hayMas = datos.pagina < datos.paginas;
  // Nada para sugerir: la banda no se dibuja.
  if (datos.entradas.length === 0 && !hayMas) return null;

  const botonVerMas = (className: string) => (
    <button
      type="button"
      data-ver-mas
      onClick={() => void verMas()}
      disabled={cargandoMas}
      className={cn(
        "h-11 flex-none cursor-pointer items-center gap-2 rounded-full bg-raised-2 px-4 text-sm font-semibold text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-wait",
        className
      )}
    >
      {cargandoMas && (
        <LoaderCircle aria-hidden="true" className="size-4 motion-safe:animate-spin" />
      )}
      {t("lists.suggestions.showMore")}
    </button>
  );

  return (
    <section
      ref={seccion}
      aria-labelledby={tituloId}
      aria-busy={cargandoMas}
      className="flex flex-col gap-3.5 border-t border-line pt-7 md:gap-7 md:pt-10"
    >
      <div className="flex items-end gap-4">
        <div className="flex flex-col gap-2">
          <h2
            id={tituloId}
            tabIndex={-1}
            className="font-display text-[2rem] leading-none focus-visible:outline-2 focus-visible:outline-ring md:text-[2.5rem]"
          >
            {t("lists.suggestions.title")}
          </h2>
          <p className="text-sm text-fg-2 md:text-[0.9375rem]">
            {t(datos.nombreUsado ? "lists.suggestions.basisWithName" : "lists.suggestions.basis", {
              count: cantidad,
            })}
          </p>
        </div>
        {hayMas && botonVerMas("ml-auto hidden md:inline-flex")}
      </div>

      {datos.entradas.length > 0 && (
        <ul className="md:grid md:grid-cols-3 md:gap-x-[2.875rem] md:gap-y-8">
          {datos.entradas.map((sugerencia) => {
            const clave = claveDeSugerencia(sugerencia);
            const href = routes.title(sugerencia.tipo, sugerencia.id_tmdb, `list-${listaId}`);
            const src = fallidos.includes(clave) ? null : tmdbImage(sugerencia.poster, "w185");
            const tipo = t(
              sugerencia.tipo === "movie" ? "common.content.movie" : "common.content.tvShow"
            );
            return (
              <li
                key={clave}
                data-sugerencia={clave}
                className="flex min-w-0 items-center gap-3.5 border-b border-line py-3 md:gap-[1.125rem] md:border-b-0 md:py-0"
              >
                <Link
                  href={href}
                  className="relative block h-24 w-16 flex-none overflow-hidden rounded-md bg-raised-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:h-[6.9375rem] md:w-[4.625rem] md:rounded-[0.4375rem]"
                >
                  {src ? (
                    <Image
                      loader={tmdbLoader}
                      src={src}
                      alt={t("common.media.posterAlt", { title: sugerencia.titulo })}
                      fill
                      sizes="(min-width: 768px) 74px, 64px"
                      className="object-cover"
                      onError={() => setFallidos((anteriores) => [...anteriores, clave])}
                    />
                  ) : (
                    <span
                      role="img"
                      aria-label={t("common.media.noPoster")}
                      className="flex h-full items-center justify-center p-1 text-center text-[0.6875rem] text-fg-3 md:text-[0.8125rem]"
                    >
                      {t("common.media.noPoster")}
                    </span>
                  )}
                </Link>
                <span className="flex min-w-0 flex-col gap-1 md:gap-[0.3125rem]">
                  <Link
                    href={href}
                    data-titulo
                    lang={sugerencia.campos_en_ingles?.includes("titulo") ? "en" : undefined}
                    className="text-base leading-tight font-semibold break-words text-foreground no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:text-lg md:leading-tight"
                  >
                    {sugerencia.titulo}
                  </Link>
                  <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[0.8125rem] text-fg-3 md:gap-x-[0.5625rem] md:text-[0.9375rem]">
                    <span className="whitespace-nowrap">
                      {tipo}
                      {sugerencia.anio !== null && ` · ${sugerencia.anio}`}
                    </span>
                    {sugerencia.calificacion_promedio !== null && (
                      <span className="inline-flex items-center gap-1 text-fg-2 md:gap-[0.3125rem]">
                        <span className="sr-only">
                          {t("common.media.tmdbRatingLabel", {
                            rating: formats.rating(sugerencia.calificacion_promedio),
                          })}
                        </span>
                        <StarIcon className="size-3 fill-primary md:size-3.5" />
                        <span aria-hidden="true">
                          {formats.rating(sugerencia.calificacion_promedio)}
                        </span>
                      </span>
                    )}
                  </span>
                  {/* `after`: el área táctil llega a 44 px sin agrandar el botón. */}
                  <button
                    type="button"
                    data-agregar
                    aria-label={t("lists.suggestions.addLabel", {
                      title: sugerencia.titulo,
                      listName: nombre,
                    })}
                    onClick={() => void agregar(sugerencia)}
                    disabled={agregando === clave}
                    className="relative mt-1 inline-flex h-[1.875rem] cursor-pointer items-center gap-[0.3125rem] self-start rounded-full bg-raised-2 pr-3 pl-2 text-xs font-semibold text-foreground after:absolute after:-inset-x-1 after:-inset-y-[0.4375rem] hover:bg-line focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-wait md:mt-[0.3125rem] md:h-[2.125rem] md:gap-1.5 md:pr-3.5 md:pl-[0.5625rem] md:text-sm md:after:-inset-y-[0.3125rem]"
                  >
                    <Plus aria-hidden="true" strokeWidth={2.2} className="size-3.5 md:size-4" />
                    {t("lists.suggestions.add")}
                  </button>
                </span>
              </li>
            );
          })}
        </ul>
      )}

      {hayMas && botonVerMas("inline-flex self-start md:hidden")}
    </section>
  );
}
