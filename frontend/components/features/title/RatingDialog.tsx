"use client";

import { useId, useState } from "react";
import { Eye, X } from "lucide-react";
import { useTranslations } from "next-intl";

import { DialogShell } from "@/components/features/title/DialogShell";
import { StarRating } from "@/components/features/title/StarRating";
import { translateError } from "@/lib/errors";

const MAX_TEXTO = 1000;
const ESTRELLA =
  "12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2";

function Nota({ valor }: { valor: number }) {
  return (
    <span className="inline-flex items-center gap-1 tabular-nums">
      <svg aria-hidden="true" viewBox="0 0 24 24" className="size-3.5 fill-primary">
        <polygon points={ESTRELLA} />
      </svg>
      {valor}
    </span>
  );
}

export function mensajeDeError(error: unknown) {
  return error instanceof Error && error.message
    ? error.message
    : translateError({ code: "unknown" });
}

/**
 * Calificar o editar (doc 04 §5d, canvas). No llama a la API: avisa con
 * `onSubmit` y la ficha decide qué pedir y qué toast mostrar. Si `onSubmit`
 * falla, el error queda a la vista y el diálogo sigue abierto.
 */
export function RatingDialog({
  titulo,
  enVistas,
  inicial,
  onSubmit,
  onRemoveRating,
  onClose,
}: {
  titulo: string;
  enVistas: boolean;
  inicial?: { valor: number; texto: string | null };
  onSubmit: (datos: { valor: number; texto: string }) => Promise<void>;
  onRemoveRating?: () => void;
  onClose: () => void;
}) {
  const t = useTranslations();
  const editando = inicial !== undefined;
  const [valor, setValor] = useState(inicial?.valor ?? 0);
  const [preview, setPreview] = useState(0);
  const [texto, setTexto] = useState(inicial?.texto ?? "");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tituloId = useId();
  const notaId = useId();
  const textoId = useId();
  const vista = preview || valor;

  async function publicar() {
    if (!valor || enviando) return;
    setEnviando(true);
    setError(null);
    try {
      await onSubmit({ valor, texto: texto.trim() });
    } catch (motivo) {
      setError(mensajeDeError(motivo));
      setEnviando(false);
    }
  }

  return (
    <DialogShell
      labelledBy={tituloId}
      onClose={onClose}
      busy={enviando}
      initialFocus={(dialog) => dialog.querySelector<HTMLElement>('[role="radio"][tabindex="0"]')}
    >
      <div className="flex items-start justify-between gap-4">
        <h2 id={tituloId} className="font-display text-[32px] leading-none md:text-[36px]">
          {editando ? t("title.rating.edit") : t("title.rating.titleLabel", { title: titulo })}
        </h2>
        <button
          type="button"
          aria-label={t("common.actions.close")}
          onClick={onClose}
          disabled={enviando}
          className="-mt-2 -mr-2 grid size-11 shrink-0 cursor-pointer place-items-center rounded-lg text-fg-3 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          <X aria-hidden="true" className="size-5" />
        </button>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-sm font-semibold">
            <span id={notaId}>{t("common.rating.label")}</span>
            <span aria-live="polite">
              {vista ? (
                <>
                  : <Nota valor={vista} />
                </>
              ) : (
                <span className="ml-1.5 font-normal text-fg-3">{t("title.rating.rangeHint")}</span>
              )}
            </span>
          </span>
          {editando && valor > 0 && valor !== inicial.valor && (
            <span className="text-[13px] text-fg-3">
              {t("title.rating.previousLabel")} <Nota valor={inicial.valor} />
            </span>
          )}
        </div>
        <StarRating
          value={valor}
          onChange={setValor}
          onPreview={setPreview}
          labelledBy={notaId}
          disabled={enviando}
        />
      </div>

      {!enVistas && (
        <p className="flex items-center gap-2.5 text-sm text-fg-2">
          <Eye aria-hidden="true" className="size-[18px] shrink-0" />
          {t("title.rating.watchedHelp", { title: titulo })}
        </p>
      )}

      <div className="flex flex-col gap-2">
        <label htmlFor={textoId} className="text-sm font-semibold">
          {t("common.review.label")}{" "}
          <span className="font-normal text-fg-3">{t("common.fields.optionalHint")}</span>
        </label>
        <textarea
          id={textoId}
          rows={6}
          maxLength={MAX_TEXTO}
          value={texto}
          onChange={(event) => setTexto(event.target.value)}
          placeholder={t("title.review.placeholder")}
          disabled={enviando}
          className="w-full resize-y rounded-lg bg-background px-4 py-3.5 text-base leading-[1.55] shadow-[inset_0_0_0_1px_var(--line)] placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-ring"
        />
        <span className="self-end text-[13px] text-fg-3 tabular-nums">
          {texto.length}/{MAX_TEXTO}
        </span>
      </div>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      {/* Celular: Cancel y la acción en dos columnas y «Remove rating» centrado
          debajo (canvas); escritorio: todo en una fila. Son los mismos botones. */}
      <div className="flex flex-col gap-2.5 md:flex-row md:items-center">
        {editando && onRemoveRating && (
          <button
            type="button"
            onClick={onRemoveRating}
            disabled={enviando}
            className="order-last h-11 cursor-pointer self-center px-3 font-semibold text-destructive focus-visible:outline-2 focus-visible:outline-ring md:order-none md:self-auto md:px-2"
          >
            {t("common.rating.remove")}
          </button>
        )}
        <span className="hidden flex-1 md:block" />
        <div className="grid grid-cols-2 gap-2.5 md:flex">
          <button
            type="button"
            onClick={onClose}
            disabled={enviando}
            className="h-[52px] cursor-pointer rounded-lg px-4 font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring md:h-12 md:font-medium md:shadow-none"
          >
            {t("common.actions.cancel")}
          </button>
          <button
            type="button"
            onClick={publicar}
            disabled={!valor || enviando}
            className="h-[52px] cursor-pointer rounded-lg bg-primary px-6 font-semibold text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-40 md:h-12"
          >
            {editando ? t("common.actions.update") : t("common.review.publish")}
          </button>
        </div>
      </div>
    </DialogShell>
  );
}
