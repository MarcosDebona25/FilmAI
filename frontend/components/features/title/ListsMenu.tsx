"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { Check, Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";

import { mantenerFocoEnDialogo } from "@/lib/dialog-focus";
import { ApiError, extraerErroresPorCampo } from "@/lib/api";
import { posicionarMenu } from "@/lib/posicion-menu";
import type { ListaFicha } from "@/lib/title-lists";
import { mensajeDeError } from "@/components/features/title/RatingDialog";

/**
 * Menú «Add to list» (canvas): las listas propias con su casilla, y crear una
 * nueva en el lugar. En escritorio es un panel pegado al botón, que se abre
 * hacia donde haya lugar y lo sigue si la página se desplaza; en celular, una
 * hoja desde abajo con fondo oscuro y la página quieta. Es un `<dialog>` modal
 * nativo: el fondo queda inerte, Escape y el clic afuera lo cierran.
 */
function ubicar(dialogo: HTMLDialogElement) {
  // El diálogo modal vive en la capa superior, fuera del flujo: su posición se
  // calcula a mano desde el contenedor del botón. `scrollHeight` da el alto
  // completo del contenido aunque hoy esté recortado por el alto máximo.
  const ancla = dialogo.parentElement?.getBoundingClientRect();
  if (!ancla) return;
  const { x, y, altoMaximo } = posicionarMenu({
    ancla,
    ancho: dialogo.offsetWidth,
    alto: dialogo.scrollHeight,
    ventana: { ancho: window.innerWidth, alto: window.innerHeight },
  });
  dialogo.style.setProperty("--menu-x", `${x}px`);
  dialogo.style.setProperty("--menu-y", `${y}px`);
  dialogo.style.setProperty("--menu-max", `${altoMaximo}px`);
}

export function ListsMenu({
  titulo,
  listas,
  pendiente,
  onAlternar,
  onCrear,
  onClose,
}: {
  titulo: string;
  listas: ListaFicha[];
  pendiente: number | null;
  onAlternar: (lista: ListaFicha) => void;
  onCrear: (nombre: string) => Promise<void>;
  onClose: () => void;
}) {
  const t = useTranslations();
  const ref = useRef<HTMLDialogElement>(null);
  const [creando, setCreando] = useState(false);
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const tituloId = useId();
  const campoId = useId();

  useEffect(() => {
    const dialogo = ref.current;
    if (!dialogo) return;
    dialogo.showModal();
    ubicar(dialogo);
    dialogo.querySelector<HTMLElement>("button, input")?.focus({ preventScroll: true });

    const seguirAlBoton = () => ubicar(dialogo);
    window.addEventListener("scroll", seguirAlBoton, { passive: true });
    window.addEventListener("resize", seguirAlBoton);
    const desborde = document.body.style.overflow;
    if (!window.matchMedia?.("(min-width: 48rem)").matches) {
      document.body.style.overflow = "hidden";
    }
    return () => {
      dialogo.close();
      window.removeEventListener("scroll", seguirAlBoton);
      window.removeEventListener("resize", seguirAlBoton);
      document.body.style.overflow = desborde;
    };
  }, []);

  // El formulario de lista nueva y sus errores cambian el alto del panel.
  useLayoutEffect(() => {
    if (ref.current?.open) ubicar(ref.current);
  }, [creando, error, listas.length]);

  async function crear(event: FormEvent) {
    event.preventDefault();
    const limpio = nombre.trim();
    if (!limpio) {
      setError(t("title.lists.nameRequiredError"));
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await onCrear(limpio);
      setCreando(false);
      setNombre("");
    } catch (motivo) {
      setError(
        motivo instanceof ApiError && motivo.code === "list_name_duplicated"
          ? t("title.lists.nameDuplicateError")
          : motivo instanceof ApiError
            ? (extraerErroresPorCampo(motivo).nombre ?? motivo.message)
            : mensajeDeError(motivo)
      );
    } finally {
      setEnviando(false);
    }
  }

  const fila =
    "flex min-h-11 w-full cursor-pointer items-center gap-3 rounded-[0.625rem] px-3 text-left text-[0.9375rem] hover:bg-raised-2 focus-visible:outline-2 focus-visible:outline-ring";

  return (
    <dialog
      ref={ref}
      aria-label={t("title.lists.addTitleLabel", { title: titulo })}
      aria-modal="true"
      onKeyDown={(event) => mantenerFocoEnDialogo(event.nativeEvent, ref.current)}
      onCancel={(event) => {
        // Escape: se desmonta desde el padre, que también devuelve el foco.
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        // Clic en el fondo (o fuera de la hoja): el `<dialog>` es el objetivo.
        if (event.target !== ref.current) return;
        const caja = ref.current.getBoundingClientRect();
        const { clientX: x, clientY: y } = event;
        if (x < caja.left || x > caja.right || y < caja.top || y > caja.bottom) onClose();
      }}
      className="fixed inset-x-0 top-auto bottom-0 m-0 max-h-[80dvh] w-full max-w-none flex-col gap-0.5 overflow-y-auto overscroll-contain rounded-t-[1.25rem] border-0 bg-raised px-3 pt-2.5 pb-6 text-foreground shadow-[0_-10px_40px_rgb(0_0_0/0.4)] backdrop:bg-black/55 open:flex md:inset-x-auto md:top-[var(--menu-y)] md:bottom-auto md:left-[var(--menu-x)] md:max-h-[var(--menu-max)] md:w-[21.25rem] md:overscroll-auto md:rounded-[0.875rem] md:p-2 md:shadow-[0_18px_46px_rgb(0_0_0/0.45),inset_0_0_0_1px_var(--line)] md:backdrop:bg-transparent"
    >
      <span aria-hidden="true" className="mx-auto mb-2 h-1 w-10 rounded-full bg-line md:hidden" />
      <div className="flex items-center justify-between px-2 pb-2 md:hidden">
        <h2 id={tituloId} className="font-display text-[1.875rem] leading-none">
          {t("common.lists.add")}
        </h2>
        <button
          type="button"
          aria-label={t("common.actions.close")}
          onClick={onClose}
          className="-mr-1.5 grid size-11 cursor-pointer place-items-center text-fg-2"
        >
          <X aria-hidden="true" className="size-5" />
        </button>
      </div>
      <p className="mx-3 my-1.5 text-[0.8125rem] font-semibold text-fg-3">
        {t("title.lists.heading")}
      </p>
      {listas.map((lista) => (
        <button
          key={lista.id}
          type="button"
          aria-pressed={lista.contiene}
          disabled={pendiente === lista.id}
          onClick={() => onAlternar(lista)}
          className={`${fila} font-medium`}
        >
          <span
            aria-hidden="true"
            className={`grid size-[1.375rem] shrink-0 place-items-center rounded-md ${lista.contiene ? "bg-primary text-on-accent" : "shadow-[inset_0_0_0_1.5px_var(--fg-3)]"}`}
          >
            {lista.contiene && <Check className="size-3.5" strokeWidth={3} />}
          </span>
          <span className="min-w-0 flex-1 truncate">{lista.nombre}</span>
          <span className="text-[0.8125rem] text-fg-3 tabular-nums">{lista.cantidad_items}</span>
        </button>
      ))}
      <span aria-hidden="true" className="mx-1 my-1.5 h-px bg-line" />
      {creando ? (
        <form onSubmit={crear} className="flex flex-col gap-2 px-3 py-1.5">
          <label htmlFor={campoId} className="text-sm font-semibold">
            {t("title.lists.newNameLabel")}
          </label>
          <input
            id={campoId}
            type="text"
            maxLength={80}
            value={nombre}
            onChange={(event) => setNombre(event.target.value)}
            placeholder={t("title.lists.nameExamplePlaceholder")}
            aria-invalid={error ? true : undefined}
            disabled={enviando}
            className="h-11 rounded-lg bg-background px-3 shadow-[inset_0_0_0_1px_var(--field-border)] placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-ring"
          />
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setCreando(false);
                setError(null);
              }}
              className="h-11 cursor-pointer rounded-lg px-3 text-fg-2 hover:text-foreground md:h-10"
            >
              {t("common.actions.cancel")}
            </button>
            <button
              type="submit"
              disabled={enviando}
              className="h-11 cursor-pointer rounded-lg bg-primary px-4 font-semibold text-primary-foreground disabled:opacity-60 md:h-10"
            >
              {t("title.lists.createAndAdd")}
            </button>
          </div>
        </form>
      ) : (
        <button type="button" onClick={() => setCreando(true)} className={`${fila} font-semibold`}>
          <Plus aria-hidden="true" className="size-5 shrink-0 text-primary" />
          {t("title.lists.newAction")}
        </button>
      )}
      <p className="mx-3 mt-1.5 mb-1 text-[0.8125rem] text-fg-3">{t("title.lists.defaultsHint")}</p>
      <button
        type="button"
        onClick={onClose}
        className="mt-2 h-12 cursor-pointer rounded-lg bg-raised-2 font-semibold md:hidden"
      >
        {t("common.actions.done")}
      </button>
    </dialog>
  );
}
