"use client";

import { useId } from "react";
import { Check } from "lucide-react";
import { useTranslations } from "next-intl";

import { SegmentedPills, SheetFooter, SheetHeader } from "@/components/features/filters/SheetParts";
import { DialogShell } from "@/components/features/title/DialogShell";
import {
  CLASES,
  ETIQUETA_CLASE,
  ETIQUETA_ORDEN_LISTA,
  ORDENES_LISTA,
  type FiltrosLista,
} from "@/lib/lists";
import { NOTAS, etiquetaNota } from "@/lib/search";
import { cn } from "@/lib/utils";

/**
 * Hoja «Filters and sort» del detalle de una lista en celular (canvas «List
 * detail · mobile»). Cada cambio se aplica al momento; «Show N results» solo
 * cierra, con el total que ya trajo la lista.
 */
export function ListFiltersSheet({
  filtros,
  total,
  onCambiar,
  onLimpiar,
  onClose,
}: {
  filtros: FiltrosLista;
  total: number | null;
  onCambiar: (cambios: Partial<FiltrosLista>) => void;
  onLimpiar: () => void;
  onClose: () => void;
}) {
  const t = useTranslations();
  const titulo = useId();
  const leyenda = "mb-2.5 p-0 text-[13px] font-semibold text-fg-3";

  return (
    <DialogShell labelledBy={titulo} onClose={onClose}>
      <SheetHeader id={titulo} titulo={t("lists.detail.filtersTitle")} onClose={onClose} />

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
        <legend className={leyenda}>{t("common.rating.tmdbLabel")}</legend>
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
          {ORDENES_LISTA.map((orden) => {
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
                {t(ETIQUETA_ORDEN_LISTA[orden])}
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
            : t("lists.detail.resultsAction", { count: total })
        }
      />
    </DialogShell>
  );
}
