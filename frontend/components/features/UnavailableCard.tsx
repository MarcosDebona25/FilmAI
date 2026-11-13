import { ListPlus, ImageOff } from "lucide-react";
import { useTranslations } from "next-intl";

import { useFormats } from "@/lib/format";

/**
 * El lugar de un título que TMDB ya no tiene (lápida) en una grilla de lista.
 * Es gris y no lleva a ninguna parte: no hay ficha a la que ir. El usuario
 * conserva el botón de quitar de la lista, que pone el que la usa.
 */
export function UnavailableCard({
  addedAt,
  compact = false,
}: {
  addedAt?: string;
  /** La fila del chat: la miniatura gris con el aviso al lado, en vez de la grilla. */
  compact?: boolean;
}) {
  const t = useTranslations("common");
  const formats = useFormats();

  if (compact) {
    return (
      <div className="grid grid-cols-[2.75rem_minmax(0,1fr)] items-center gap-3 py-2 text-fg-3 md:grid-cols-[3rem_minmax(0,1fr)] md:gap-3.5 md:py-2.5">
        <span className="flex aspect-[2/3] w-full items-center justify-center rounded-md bg-raised">
          <ImageOff aria-hidden="true" className="size-5" />
        </span>
        <span className="text-sm font-semibold">{t("content.titleUnavailable")}</span>
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col gap-2.5 md:gap-3">
      <span className="flex aspect-[2/3] flex-col items-center justify-center gap-2 rounded-lg bg-raised p-3 text-center text-fg-3">
        <ImageOff aria-hidden="true" className="size-6" />
        <span className="text-sm font-semibold md:text-[0.9375rem]">
          {t("content.titleUnavailable")}
        </span>
      </span>
      {addedAt && (
        <time
          dateTime={addedAt}
          className="inline-flex items-center gap-1 text-[0.6875rem] text-fg-3 tabular-nums"
        >
          <ListPlus className="size-[0.6875rem]" aria-hidden="true" />
          <span className="sr-only">
            {t("media.addedOnLabel", { date: formats.dateShort(addedAt) })}
          </span>
          <span aria-hidden="true">{formats.dateShort(addedAt)}</span>
        </time>
      )}
    </div>
  );
}
