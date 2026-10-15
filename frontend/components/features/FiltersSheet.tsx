"use client";

import { useId } from "react";
import { useTranslations } from "next-intl";

import { SegmentedPills, SheetFooter, SheetHeader } from "@/components/features/filters/SheetParts";
import { DialogShell } from "@/components/features/title/DialogShell";
import {
  NOTAS,
  etiquetaNota,
  opcionesDeAnio,
  anioDesdeOpcion,
  opcionDeAnio,
  type Busqueda,
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
  const campo =
    "h-12 w-full cursor-pointer rounded-full border-0 bg-background px-3.5 text-base font-semibold text-foreground shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";
  const etiqueta = "text-[13px] font-semibold text-fg-3";

  return (
    <DialogShell labelledBy={titulo} onClose={onClose}>
      <SheetHeader id={titulo} titulo={t("common.filters.title")} onClose={onClose} />

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
        <SegmentedPills
          opciones={[null, ...NOTAS]}
          valor={busqueda.nota}
          onCambiar={(nota) => onCambiar({ nota })}
          etiqueta={(nota) => etiquetaNota(t, nota, true)}
          etiquetaAccesible={(nota) => etiquetaNota(t, nota)}
          className="grid-cols-4 rounded-3xl"
        />
      </fieldset>

      <SheetFooter
        onLimpiar={() => onCambiar({ genero: null, anio: null, nota: null })}
        onAplicar={onClose}
        aplicar={t("search.filters.apply")}
      />
    </DialogShell>
  );
}
