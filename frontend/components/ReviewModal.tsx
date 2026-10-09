"use client";

import { useLocale } from "next-intl";
import { translateError } from "@/lib/errors";
import { useRef, useState } from "react";
import { Star, LoaderCircle } from "lucide-react";
import { Modal } from "@/components/Modal";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { cambiosResena, ReviewValidationError, type MiResena } from "@/lib/reviews";

export function ReviewModal({
  item,
  action,
  onClose,
  onSuccess,
}: {
  item: MiResena;
  action: "edit" | "text" | "rating";
  onClose: () => void;
  onSuccess: (updated: MiResena | null) => void;
}) {
  const locale = useLocale();
  const [valor, setValor] = useState(item.valor);
  const [hover, setHover] = useState<number | null>(null);
  const [texto, setTexto] = useState(item.texto ?? "");
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);
  async function submit() {
    if (inFlight.current) return;
    setError(null);
    let body;
    try {
      if (action === "edit") body = cambiosResena(item, valor, texto);
    } catch (err) {
      setError(
        translateError(err instanceof ReviewValidationError ? err : { code: "unknown" }, locale)
      );
      textRef.current?.focus();
      return;
    }
    if (action === "edit" && !Object.keys(body ?? {}).length) {
      onClose();
      return;
    }
    inFlight.current = true;
    setBusy(true);
    try {
      if (action === "edit") {
        const updated = await apiFetch<MiResena>(`/api/reviews/${item.id}/`, {
          method: "PUT",
          body,
        });
        onSuccess({ ...item, ...updated });
      } else {
        await apiFetch(`/api/reviews/${item.id}/${action === "text" ? "texto/" : ""}`, {
          method: "DELETE",
        });
        onSuccess(action === "text" ? { ...item, texto: null } : null);
      }
    } catch {
      setError("No pudimos guardar el cambio. Tus datos se mantienen; intentá de nuevo.");
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  const title =
    action === "edit"
      ? `Editar calificación y reseña de "${item.titulo}"`
      : action === "text"
        ? "¿Eliminar reseña?"
        : "¿Quitar tu calificación?";
  return (
    <Modal
      title={title}
      onClose={onClose}
      busy={busy}
      initialFocusRef={action === "edit" ? textRef : undefined}
    >
      {action !== "edit" && <p className="mt-3 break-words font-medium">{item.titulo}</p>}
      {action === "edit" ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
          className="mt-4 space-y-4"
        >
          <fieldset disabled={busy}>
            <legend className="mb-2 text-sm font-medium">Calificación (1 a 10)</legend>
            <div className="grid grid-cols-5 sm:flex" onMouseLeave={() => setHover(null)}>
              {Array.from({ length: 10 }, (_, index) => index + 1).map((n) => (
                <label
                  key={n}
                  className="relative flex min-h-11 min-w-0 flex-1 cursor-pointer items-center justify-center rounded focus-within:outline-2 focus-within:outline-ring"
                  onMouseEnter={() => setHover(n)}
                >
                  <input
                    type="radio"
                    name="valor"
                    value={n}
                    checked={valor === n}
                    onChange={() => setValor(n)}
                    aria-label={`${n} de 10`}
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                  />
                  <Star
                    aria-hidden="true"
                    className={`size-6 ${n <= (hover ?? valor) ? "fill-primary text-primary" : hover !== null && n <= item.valor ? "fill-primary/20 text-primary/40" : "text-muted-foreground"}`}
                  />
                </label>
              ))}
            </div>
            <p className="mt-1 tabular-nums" aria-live="polite">
              {valor}/10
            </p>
          </fieldset>
          <div>
            <label htmlFor="review-text" className="block text-sm font-medium">
              Reseña (opcional)
            </label>
            <textarea
              ref={textRef}
              id="review-text"
              name="texto"
              value={texto}
              maxLength={1000}
              disabled={busy}
              rows={6}
              aria-describedby="review-count review-error"
              aria-invalid={Boolean(error)}
              onChange={(event) => setTexto(event.target.value)}
              onKeyDown={(event) => {
                if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                  event.preventDefault();
                  void submit();
                }
              }}
              className="mt-1 w-full rounded-lg border border-input bg-background p-3 text-base focus-visible:outline-2 focus-visible:outline-ring"
            />
            <p id="review-count" className="text-sm tabular-nums">
              {texto.length}/1000
            </p>
          </div>
          {error && (
            <p id="review-error" role="alert" className="text-red-700 dark:text-red-400">
              {error}
            </p>
          )}
          <div className="flex flex-wrap justify-end gap-3">
            <Button
              className="min-h-11"
              type="button"
              variant="secondary"
              disabled={busy}
              onClick={onClose}
            >
              Cancelar
            </Button>
            <Button className="min-h-11" type="submit" disabled={busy}>
              {busy && <LoaderCircle aria-hidden="true" className="motion-safe:animate-spin" />}
              Actualizar
            </Button>
          </div>
        </form>
      ) : (
        <>
          <p className="mt-3">
            {action === "text"
              ? `Se eliminará el texto de tu reseña. Tu calificación de ${item.valor}/10 y la producción en Vistas se conservan. El texto no se puede recuperar.`
              : `Se eliminará tu calificación de ${item.valor}/10${item.texto ? " y tu reseña" : ""}, y ${item.titulo} dejará de estar en Vistas. ${item.texto ? "La calificación y la reseña no se pueden recuperar" : "La calificación no se puede recuperar"}; a Vistas podés volver a agregarla cuando quieras.`}
          </p>
          {action === "rating" && item.texto && (
            <details className="mt-3">
              <summary className="min-h-11 cursor-pointer">Ver reseña completa</summary>
              <p className="whitespace-pre-wrap break-words">{item.texto}</p>
            </details>
          )}
          {error && (
            <p role="alert" className="mt-3 text-red-700 dark:text-red-400">
              {error}
            </p>
          )}
          <div className="mt-6 flex flex-wrap justify-end gap-3">
            <Button className="min-h-11" variant="secondary" disabled={busy} onClick={onClose}>
              Cancelar
            </Button>
            <Button
              className="min-h-11"
              variant="destructive"
              disabled={busy}
              onClick={() => void submit()}
            >
              {busy && <LoaderCircle aria-hidden="true" className="motion-safe:animate-spin" />}
              {action === "text" ? "Eliminar reseña" : "Quitar calificación"}
            </Button>
          </div>
        </>
      )}
    </Modal>
  );
}
