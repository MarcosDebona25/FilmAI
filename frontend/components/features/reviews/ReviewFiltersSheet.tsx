"use client";

import { useId } from "react";
import { Check } from "lucide-react";
import { useTranslations } from "next-intl";

import { SegmentedPills, SheetFooter, SheetHeader } from "@/components/features/filters/SheetParts";
import { DialogShell } from "@/components/features/title/DialogShell";
import { CLASES, PRESENCIAS, type FiltrosResenas } from "@/lib/my-reviews";
import { ETIQUETA_ORDEN, ORDENES } from "@/lib/review-filters";
import { NOTAS, etiquetaNota } from "@/lib/search";
import { cn } from "@/lib/utils";

export const ETIQUETA_PRESENCIA = { with: "withReview", without: "withoutReview" } as const;
export const ETIQUETA_CLASE = { movie: "movies", tv: "tvShows" } as const;

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

  return (
    <DialogShell labelledBy={titulo} onClose={onClose}>
      <SheetHeader id={titulo} titulo={t("reviews.filters.dialogTitle")} onClose={onClose} />

      <fieldset className="m-0 border-0 p-0">
        <legend className={leyenda}>{t("reviews.filters.presenceLabel")}</legend>
        <SegmentedPills
          opciones={[null, ...PRESENCIAS]}
          valor={filtros.resena}
          onCambiar={(resena) => onCambiar({ resena })}
          etiqueta={(resena) =>
            t(resena ? `reviews.filters.${ETIQUETA_PRESENCIA[resena]}` : "reviews.filters.all")
          }
          className="grid-cols-3 rounded-full"
        />
      </fieldset>

      <fieldset className="m-0 border-0 p-0">
        <legend className={leyenda}>{t("common.content.typeShortLabel")}</legend>
        <SegmentedPills
          opciones={[null, ...CLASES]}
          valor={filtros.clase}
          onCambiar={(clase) => onCambiar({ clase })}
          etiqueta={(clase) =>
            t(clase ? `common.content.${ETIQUETA_CLASE[clase]}` : "common.content.all")
          }
          className="grid-cols-3 rounded-full"
        />
      </fieldset>

      <fieldset className="m-0 border-0 p-0">
        <legend className={leyenda}>{t("common.rating.label")}</legend>
        <SegmentedPills
          opciones={[null, ...NOTAS]}
          valor={filtros.nota}
          onCambiar={(nota) => onCambiar({ nota })}
          etiqueta={(nota) => etiquetaNota(t, nota, true)}
          etiquetaAccesible={(nota) => etiquetaNota(t, nota)}
          className="grid-cols-4 rounded-3xl"
        />
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

      <SheetFooter
        onLimpiar={onLimpiar}
        onAplicar={onClose}
        aplicar={
          total === null
            ? t("search.filters.apply")
            : t("reviews.filters.resultsAction", { count: total })
        }
      />
    </DialogShell>
  );
}
