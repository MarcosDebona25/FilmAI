"use client";

import { useEffect, useId, useState } from "react";
import Image from "next/image";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { useAccount } from "@/components/AccountProvider";
import { Avatar } from "@/components/Avatar";
import { ConfirmDialog } from "@/components/features/title/ConfirmDialog";
import { mensajeDeError } from "@/components/features/title/RatingDialog";
import { ErrorRetry } from "@/components/ui/ErrorRetry";
import { StarIcon } from "@/components/ui/StarIcon";
import { apiFetch } from "@/lib/api";
import type { MediaType } from "@/lib/catalog";
import { useFormats } from "@/lib/format";
import {
  ETIQUETA_ORDEN,
  ORDENES,
  ORDEN_API,
  parametrosNota,
  type Orden,
} from "@/lib/review-filters";
import { NOTAS, de, etiquetaNota, type Nota } from "@/lib/search";
import type { MiCalificacion } from "@/lib/title";
import { useDesborde } from "@/lib/use-desborde";

type Resena = {
  /** `null` si la cuenta se dio de baja: la API no manda la identidad (26/10/2026). */
  nombre_usuario: string | null;
  avatar_id: number | null;
  autor_dado_de_baja: boolean;
  valor: number;
  fecha: string;
  texto: string;
};
type Pagina = {
  total: number;
  total_comunidad: number;
  next: string | null;
  results: Resena[];
};

function Nota({ valor }: { valor: number }) {
  const t = useTranslations("common.rating");
  return (
    <span className="inline-flex items-center gap-1.5 font-bold tabular-nums">
      <StarIcon className="size-[15px] fill-primary" />
      <span className="sr-only">{t("starValueLabel", { rating: String(valor) })}</span>
      <span aria-hidden="true">{valor}</span>
    </span>
  );
}

function Texto({ texto }: { texto: string }) {
  const t = useTranslations("common.text");
  const [abierto, setAbierto] = useState(false);
  const [ref, desborda] = useDesborde<HTMLParagraphElement>(abierto, texto);
  return (
    <>
      <p
        ref={ref}
        className={`leading-[1.6] whitespace-pre-line text-pretty ${abierto ? "" : "line-clamp-3"}`}
      >
        {texto}
      </p>
      {(desborda || abierto) && (
        <button
          type="button"
          aria-expanded={abierto}
          onClick={() => setAbierto(!abierto)}
          className="h-11 cursor-pointer self-start text-sm font-semibold text-fg-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring md:h-9"
        >
          {abierto ? t("readLess") : t("readMore")}
        </button>
      )}
    </>
  );
}

/**
 * «Reviews» de la ficha (canvas): la propia arriba, si tiene texto, y la
 * comunidad con orden, filtro por nota y «Load more» sobre el cursor de la API.
 * Las reseñas de la comunidad son públicas (14/10/2026).
 */
export function ReviewsSection({
  tipo,
  idTmdb,
  titulo,
  mia,
  onEditar,
  onTextoBorrado,
}: {
  tipo: MediaType;
  idTmdb: number;
  titulo: string;
  mia: MiCalificacion | null;
  onEditar: () => void;
  onTextoBorrado: () => void;
}) {
  const t = useTranslations();
  const formats = useFormats();
  const { perfil, avatares = [] } = useAccount();
  const tituloId = useId();
  const tuyaId = useId();
  const [orden, setOrden] = useState<Orden>("newest");
  const [nota, setNota] = useState<Nota | null>(null);
  const [pagina, setPagina] = useState<Pagina | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Otro intento vuelve a pedir la lista (Q-03: todo error de carga se puede reintentar).
  const [intento, setIntento] = useState(0);
  const [cargandoMas, setCargandoMas] = useState(false);
  const [borrar, setBorrar] = useState(false);

  const consulta = `/api/reviews/?${new URLSearchParams({
    id_tmdb: String(idTmdb),
    tipo,
    orden: ORDEN_API[orden],
    ...(nota && parametrosNota(nota)),
  })}`;

  useEffect(() => {
    let vigente = true;
    apiFetch<Pagina>(consulta).then(
      (datos) => {
        if (!vigente) return;
        setPagina(datos);
        setError(null);
      },
      (motivo: unknown) => vigente && setError(mensajeDeError(motivo))
    );
    return () => {
      vigente = false;
    };
  }, [consulta, intento]);

  async function cargarMas() {
    if (!pagina?.next || cargandoMas) return;
    setCargandoMas(true);
    try {
      // Solo se reusa el cursor: nunca se piden cookies a un origen que vino en la respuesta.
      const siguiente = await apiFetch<Pagina>(`/api/reviews/${new URL(pagina.next).search}`);
      setPagina({ ...siguiente, results: [...pagina.results, ...siguiente.results] });
    } catch (motivo) {
      toast.error(mensajeDeError(motivo));
    } finally {
      setCargandoMas(false);
    }
  }

  async function borrarTexto() {
    if (!mia) return;
    await apiFetch(`/api/reviews/${mia.id}/texto/`, { method: "DELETE" });
    toast.success(t("title.feedback.reviewDeleted"));
    setBorrar(false);
    onTextoBorrado();
  }

  // «today» si la fecha (AAAA-MM-DD, sin hora) es la de hoy en este dispositivo.
  const ahora = new Date();
  const hoy = [ahora.getFullYear(), ahora.getMonth() + 1, ahora.getDate()]
    .map((parte) => String(parte).padStart(2, "0"))
    .join("-");
  const fecha = (valor: string) => (valor === hoy ? t("title.reviews.today") : formats.date(valor));
  const filtrando = nota !== null;
  const avatar = (id: number) => avatares.find((opcion) => opcion.id === id)?.src;
  const pildora =
    "inline-flex h-12 items-center gap-2 rounded-full pr-1 pl-3.5 text-sm whitespace-nowrap text-fg-3 shadow-[inset_0_0_0_1px_var(--field-border)] md:h-11";
  // En celular, 44 px de alto y 16 px de letra (con menos, iOS hace zoom al tocarlo).
  const selector =
    "h-11 cursor-pointer rounded-full border-0 bg-raised-2 px-2.5 text-base font-semibold text-foreground focus-visible:outline-2 focus-visible:outline-ring md:h-9 md:text-sm";

  const conteo = pagina
    ? filtrando
      ? t("title.reviews.displayedCount", {
          shownCount: formats.number(pagina.total),
          totalCount: formats.number(pagina.total_comunidad),
        })
      : t("title.reviews.communityCount", { count: formats.number(pagina.total_comunidad) })
    : "";
  const sinCoincidencias =
    pagina !== null && pagina.total_comunidad > 0 && pagina.results.length === 0;

  return (
    <section aria-labelledby={tituloId} className="flex max-w-[880px] flex-col gap-8">
      <h2 id={tituloId} className="font-display text-[34px] leading-none md:text-[40px]">
        {t("title.reviews.heading")}
      </h2>

      {mia?.texto && perfil && (
        <article
          aria-labelledby={tuyaId}
          className="grid grid-cols-[44px_minmax(0,1fr)] gap-4 rounded-[14px] bg-raised p-5 md:p-6"
        >
          <Avatar perfil={perfil} avatares={avatares} size={44} />
          <div className="flex min-w-0 flex-col gap-2.5">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5">
              <h3 id={tuyaId} className="font-semibold">
                {t("title.reviews.yourReview")}
              </h3>
              <Nota valor={mia.valor} />
              <span className="text-sm text-fg-3">{fecha(mia.fecha)}</span>
            </div>
            <Texto texto={mia.texto} />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onEditar}
                className="inline-flex h-11 cursor-pointer items-center gap-1.5 rounded-lg px-3 text-sm font-semibold text-fg-2 md:h-10 shadow-[inset_0_0_0_1px_var(--line)] hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
              >
                <Pencil aria-hidden="true" className="size-4" />
                {t("common.actions.edit")}
              </button>
              <button
                type="button"
                onClick={() => setBorrar(true)}
                className="inline-flex h-11 cursor-pointer items-center gap-1.5 rounded-lg px-3 text-sm font-semibold text-destructive md:h-10 focus-visible:outline-2 focus-visible:outline-ring"
              >
                <Trash2 aria-hidden="true" className="size-4" />
                {t("common.review.delete")}
              </button>
            </div>
          </div>
        </article>
      )}

      <div className="flex flex-col">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-x-5 gap-y-3">
          <div className="flex items-center gap-3.5">
            {/* El contenedor vive siempre; el conteo se agrega después y se anuncia. */}
            <div aria-live="polite" className="empty:sr-only">
              {pagina && <h3 className="text-fg-2 tabular-nums">{conteo}</h3>}
            </div>
            {filtrando && (
              <button
                type="button"
                onClick={() => {
                  setNota(null);
                  setOrden("newest");
                }}
                className="h-11 cursor-pointer px-1 text-sm font-semibold text-fg-2 underline md:h-9 underline-offset-[3px] hover:text-foreground"
              >
                {t("common.filters.clear")}
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-2.5">
            <label className={pildora}>
              {t("common.filters.sortLabel")}
              <select
                value={orden}
                onChange={(event) => setOrden(de(ORDENES, event.target.value) ?? "newest")}
                className={selector}
              >
                {ORDENES.map((valor) => (
                  <option key={valor} value={valor}>
                    {t(ETIQUETA_ORDEN[valor])}
                  </option>
                ))}
              </select>
            </label>
            <label className={pildora}>
              {t("common.rating.label")}
              <select
                value={nota ?? ""}
                onChange={(event) => setNota(de(NOTAS, event.target.value))}
                className={selector}
              >
                {[null, ...NOTAS].map((valor) => (
                  <option key={valor ?? ""} value={valor ?? ""}>
                    {etiquetaNota(t, valor)}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        {error && (
          <ErrorRetry
            mensaje={error}
            onReintentar={() => {
              setError(null);
              setIntento((anterior) => anterior + 1);
            }}
            boton="pildora"
            className="py-6"
          />
        )}
        {!pagina &&
          !error &&
          [0, 1, 2].map((i) => (
            <div
              key={i}
              aria-hidden="true"
              className="grid grid-cols-[40px_minmax(0,1fr)] gap-4 border-t border-line py-[22px]"
            >
              <span className="size-10 rounded-full bg-raised" />
              <span className="flex flex-col gap-2.5 pt-1">
                <span className="h-4 w-48 rounded bg-raised" />
                <span className="h-4 w-full rounded bg-raised" />
                <span className="h-4 w-2/3 rounded bg-raised" />
              </span>
            </div>
          ))}
        {pagina?.results.map((resena, indice) => (
          <article
            // La posición y no un id: la API no manda el id de reseñas ajenas a
            // propósito, y esta lista solo crece agregando páginas al final. Con
            // el nombre, dos reseñas anónimas del mismo día chocaban.
            key={`${indice}-${resena.fecha}`}
            className="grid grid-cols-[40px_minmax(0,1fr)] gap-4 border-t border-line py-[22px]"
          >
            {resena.avatar_id !== null && avatar(resena.avatar_id) ? (
              <Image
                src={avatar(resena.avatar_id)!}
                alt=""
                width={40}
                height={40}
                className="size-10 rounded-full object-cover"
              />
            ) : (
              <span
                aria-hidden="true"
                className="grid size-10 place-items-center rounded-full bg-raised-2 font-semibold text-fg-2 uppercase"
              >
                {resena.nombre_usuario?.charAt(0) ?? "?"}
              </span>
            )}
            <div className="flex min-w-0 flex-col gap-1.5">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5">
                {resena.autor_dado_de_baja || resena.nombre_usuario === null ? (
                  <span className="font-semibold text-fg-2 italic">
                    {t("title.reviews.deletedAuthor")}
                  </span>
                ) : (
                  <span className="font-semibold">@{resena.nombre_usuario}</span>
                )}
                <Nota valor={resena.valor} />
                <span className="text-sm text-fg-3">{fecha(resena.fecha)}</span>
              </div>
              <Texto texto={resena.texto} />
            </div>
          </article>
        ))}
        {pagina && pagina.total_comunidad === 0 && (
          <p className="border-t border-line py-6 text-fg-2">{t("title.reviews.empty")}</p>
        )}
        <div role="status" className="empty:sr-only">
          {sinCoincidencias && (
            <div className="flex flex-col items-start gap-2 border-t border-line py-6 text-fg-2">
              <p>{t("title.reviews.filteredEmpty")}</p>
            </div>
          )}
        </div>
        {pagina?.next && (
          <button
            type="button"
            onClick={cargarMas}
            disabled={cargandoMas}
            className="mt-2 h-12 cursor-pointer self-start rounded-lg px-4 font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] hover:text-foreground disabled:cursor-wait focus-visible:outline-2 focus-visible:outline-ring"
          >
            {t("title.reviews.loadMore")}
          </button>
        )}
      </div>

      {borrar && mia?.texto && (
        <ConfirmDialog
          titulo={t("title.review.deleteConfirmTitle")}
          descripcion={t("title.review.deleteConfirmDescription", { title: titulo })}
          preview={mia.texto}
          confirmar={t("common.review.delete")}
          onConfirm={borrarTexto}
          onCancel={() => setBorrar(false)}
        />
      )}
    </section>
  );
}
