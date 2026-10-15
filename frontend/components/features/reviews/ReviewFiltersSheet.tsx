"use client";

import { useId } from "react";
import { Check, X } from "lucide-react";
import { useTranslations } from "next-intl";

import { DialogShell } from "@/components/features/title/DialogShell";
import { CLASES, ORDENES, PRESENCIAS, type FiltrosResenas, type Orden } from "@/lib/my-reviews";
import { ETIQUETA_NOTA, NOTAS } from "@/lib/search";
import { cn } from "@/lib/utils";

export const ETIQUETA_PRESENCIA = { with: "withReview", without: "withoutReview" } as const;
export const ETIQUETA_CLASE = { movie: "movies", tv: "tvShows" } as const;
export const ETIQUETA_ORDEN = {
  newest: "common.sort.newest",
  oldest: "common.sort.oldest",
  highest: "common.sort.highestRating",
  lowest: "common.sort.lowestRating",
} as const satisfies Record<Orden, string>;

/**
 * Hoja «Filtros y orden» de celular (canvas «Ratings & reviews · mobile»).
 * Cada cambio se aplica al momento, como en Buscar; «Ver N resultados» solo
 * cierra, con el total que ya trajo la lista.
 */
export function ReviewFiltersSheet({
  filtros,
  total,
  onCambiar,
  onLimpiar,
  onClose,
}: {
  filtros: FiltrosResenas;
  total: number | null;
  onCambiar: (cambios: Partial<FiltrosResenas>) => void;
  onLimpiar: () => void;
  onClose: () => void;
}) {
  const t = useTranslations();
  const titulo = useId();

  const leyenda = "mb-2.5 p-0 text-[13px] font-semibold text-fg-3";
  const grupo = "grid gap-1 bg-background p-1 shadow-[inset_0_0_0_1px_var(--line)]";
  const opcion = (activa: boolean) =>
    cn(
      "h-10 cursor-pointer rounded-full px-1.5 text-sm whitespace-nowrap focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
      activa ? "bg-selected font-semibold text-selected-foreground" : "font-medium text-fg-2"
    );

  return (
    <DialogShell labelledBy={titulo} onClose={onClose}>
      <div className="-mt-2 flex items-center justify-between">
        <h2 id={titulo} className="font-display text-[30px] leading-none">
          {t("reviews.filters.dialogTitle")}
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

      <fieldset className="m-0 border-0 p-0">
        <legend className={leyenda}>{t("reviews.filters.presenceLabel")}</legend>
        <div className={cn(grupo, "grid-cols-3 rounded-full")}>
          {[null, ...PRESENCIAS].map((resena) => (
            <button
              key={resena ?? "todas"}
              type="button"
              aria-pressed={filtros.resena === resena}
              onClick={() => onCambiar({ resena })}
              className={opcion(filtros.resena === resena)}
            >
              {t(resena ? `reviews.filters.${ETIQUETA_PRESENCIA[resena]}` : "reviews.filters.all")}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="m-0 border-0 p-0">
        <legend className={leyenda}>{t("common.content.typeShortLabel")}</legend>
        <div className={cn(grupo, "grid-cols-3 rounded-full")}>
          {[null, ...CLASES].map((clase) => (
            <button
              key={clase ?? "todo"}
              type="button"
              aria-pressed={filtros.clase === clase}
              onClick={() => onCambiar({ clase })}
              className={opcion(filtros.clase === clase)}
            >
              {t(clase ? `common.content.${ETIQUETA_CLASE[clase]}` : "common.content.all")}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="m-0 border-0 p-0">
        <legend className={leyenda}>{t("common.rating.label")}</legend>
        <div className={cn(grupo, "grid-cols-4 rounded-3xl")}>
          {[null, ...NOTAS].map((nota) => (
            <button
              key={nota ?? "todas"}
              type="button"
              aria-label={
                nota === null
                  ? t("common.filters.anyRating")
                  : t(`common.filters.${ETIQUETA_NOTA[nota]}`)
              }
              aria-pressed={filtros.nota === nota}
              onClick={() => onCambiar({ nota })}
              className={opcion(filtros.nota === nota)}
            >
              {nota === null
                ? t("common.filters.anyRating")
                : nota === "lt5"
                  ? t("search.filters.ratingShortBelowFive")
                  : t("search.filters.ratingShort", { value: nota })}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="m-0 border-0 p-0">
        <legend className={leyenda}>{t("common.filters.sortByLabel")}</legend>
        <div role="radiogroup" aria-label={t("common.filters.sortByLabel")} className="-mt-1.5">
          {ORDENES.map((orden) => {
            const activo = filtros.orden === orden;
            return (
              <button
                key={orden}
                type="button"
                role="radio"
                aria-checked={activo}
                onClick={() => onCambiar({ orden })}
                className={cn(
                  "flex h-12 w-full cursor-pointer items-center justify-between border-b border-line text-left text-base focus-visible:outline-2 focus-visible:outline-ring",
                  activo ? "font-semibold text-foreground" : "font-medium text-fg-2"
                )}
              >
                {t(ETIQUETA_ORDEN[orden])}
                {activo && <Check aria-hidden="true" className="size-[18px] text-primary" />}
              </button>
            );
          })}
        </div>
      </fieldset>

      <div className="mt-0.5 grid grid-cols-[auto_minmax(0,1fr)] gap-2.5">
        <button
          type="button"
          onClick={onLimpiar}
          className="h-[52px] cursor-pointer rounded-[10px] px-[18px] font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-ring"
        >
          {t("common.actions.clear")}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="h-[52px] cursor-pointer rounded-[10px] bg-primary font-semibold text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {total === null
            ? t("search.filters.apply")
            : t("reviews.filters.resultsAction", { count: total })}
        </button>
      </div>
    </DialogShell>
  );
}
