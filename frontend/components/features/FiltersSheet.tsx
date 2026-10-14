"use client";

import { useId } from "react";
import { X } from "lucide-react";
import { useTranslations } from "next-intl";

import { DialogShell } from "@/components/features/title/DialogShell";
import {
  ETIQUETA_NOTA,
  NOTAS,
  opcionesDeAnio,
  anioDesdeOpcion,
  opcionDeAnio,
  type Busqueda,
  type Nota,
} from "@/lib/search";
import { cn } from "@/lib/utils";

/**
 * Hoja «Filters» de Buscar en celular (canvas «Search · mobile»): Género, Año y
 * la nota de TMDB como botones. Cada cambio se aplica al momento (los
 * resultados se actualizan detrás); «Show results» solo cierra.
 */
export function FiltersSheet({
  busqueda,
  generos,
  onCambiar,
  onClose,
}: {
  busqueda: Busqueda;
  generos: { id: number; etiqueta: string }[];
  onCambiar: (cambios: Partial<Busqueda>) => void;
  onClose: () => void;
}) {
  const t = useTranslations();
  const titulo = useId();
  const generoId = useId();
  const anioId = useId();
  const etiquetaCorta = (nota: Nota | null) =>
    nota === null
      ? t("common.filters.anyRating")
      : nota === "lt5"
        ? t("search.filters.ratingShortBelowFive")
        : t("search.filters.ratingShort", { value: nota });
  const etiquetaLarga = (nota: Nota | null) =>
    nota === null ? t("common.filters.anyRating") : t(`common.filters.${ETIQUETA_NOTA[nota]}`);

  const campo =
    "h-12 w-full cursor-pointer rounded-full border-0 bg-background px-3.5 text-base font-semibold text-foreground shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";
  const etiqueta = "text-[13px] font-semibold text-fg-3";

  return (
    <DialogShell labelledBy={titulo} onClose={onClose}>
      <div className="-mt-2 flex items-center justify-between">
        <h2 id={titulo} className="font-display text-[30px] leading-none">
          {t("common.filters.title")}
        </h2>
        <button
          type="button"
          onClick={onClose}
          aria-label={t("common.actions.close")}
          className="-mr-2.5 grid size-11 cursor-pointer place-items-center text-fg-2 focus-visible:outline-2 focus-visible:outline-ring"
        >
          <X aria-hidden="true" className="size-5" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="flex min-w-0 flex-col gap-1.5">
          <label htmlFor={generoId} className={etiqueta}>
            {t("search.filters.genreLabel")}
          </label>
          <select
            id={generoId}
            value={busqueda.genero ?? ""}
            onChange={(evento) =>
              onCambiar({ genero: evento.target.value ? Number(evento.target.value) : null })
            }
            className={campo}
          >
            <option value="">{t("search.filters.allGenres")}</option>
            {generos.map((genero) => (
              <option key={genero.id} value={genero.id}>
                {genero.etiqueta}
              </option>
            ))}
          </select>
        </div>
        <div className="flex min-w-0 flex-col gap-1.5">
          <label htmlFor={anioId} className={etiqueta}>
            {t("search.filters.yearLabel")}
          </label>
          <select
            id={anioId}
            value={opcionDeAnio(busqueda.anio)}
            onChange={(evento) => onCambiar({ anio: anioDesdeOpcion(evento.target.value) })}
            className={campo}
          >
            <option value="">{t("search.filters.anyYear")}</option>
            <option value="upcoming">{t("search.filters.upcoming")}</option>
            {opcionesDeAnio(new Date().getFullYear()).map((opcion) => (
              <option key={opcion.valor} value={opcion.valor}>
                {opcion.decada === null
                  ? opcion.valor
                  : t("search.filters.decade", { decade: String(opcion.decada) })}
              </option>
            ))}
          </select>
        </div>
      </div>

      <fieldset className="m-0 flex flex-col border-0 p-0">
        <legend className={cn(etiqueta, "mb-2.5 p-0")}>
          {t("search.filters.tmdbRatingLabel")}
        </legend>
        <div className="grid grid-cols-4 gap-1 rounded-3xl bg-background p-1 shadow-[inset_0_0_0_1px_var(--line)]">
          {[null, ...NOTAS].map((nota) => {
            const activa = busqueda.nota === nota;
            return (
              <button
                key={nota ?? "todas"}
                type="button"
                aria-label={etiquetaLarga(nota)}
                aria-pressed={activa}
                onClick={() => onCambiar({ nota })}
                className={cn(
                  "h-10 cursor-pointer rounded-full px-1.5 text-sm whitespace-nowrap focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
                  activa
                    ? "bg-selected font-semibold text-selected-foreground"
                    : "font-medium text-fg-2"
                )}
              >
                {etiquetaCorta(nota)}
              </button>
            );
          })}
        </div>
      </fieldset>

      <div className="mt-0.5 grid grid-cols-[auto_minmax(0,1fr)] gap-2.5">
        <button
          type="button"
          onClick={() => onCambiar({ genero: null, anio: null, nota: null })}
          className="h-[52px] cursor-pointer rounded-[10px] px-[18px] font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-ring"
        >
          {t("common.actions.clear")}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="h-[52px] cursor-pointer rounded-[10px] bg-primary font-semibold text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {t("search.filters.apply")}
        </button>
      </div>
    </DialogShell>
  );
}
