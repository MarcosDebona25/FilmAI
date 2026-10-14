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
import { apiFetch } from "@/lib/api";
import type { MediaType } from "@/lib/catalog";
import { useFormats } from "@/lib/format";
import type { MiCalificacion } from "@/lib/title";
import { useDesborde } from "@/lib/use-desborde";

const ESTRELLA =
  "12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2";

type Resena = {
  nombre_usuario: string;
  avatar_id: number;
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

// Opciones del canvas → parámetros de la API («Below 5» es `nota_max=4`).
const FILTROS: Record<string, string> = {
  "0": "",
  "9+": "&nota_min=9",
  "8+": "&nota_min=8",
  "7+": "&nota_min=7",
  "6+": "&nota_min=6",
  "5+": "&nota_min=5",
  m5: "&nota_max=4",
};

function Nota({ valor }: { valor: number }) {
  return (
    <span className="inline-flex items-center gap-1.5 font-bold tabular-nums">
      <svg aria-hidden="true" viewBox="0 0 24 24" className="size-[15px] fill-primary">
        <polygon points={ESTRELLA} />
      </svg>
      {valor}
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
          className="cursor-pointer self-start text-sm font-semibold text-fg-2 hover:text-foreground"
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
  const [orden, setOrden] = useState("fecha-desc");
  const [nota, setNota] = useState("0");
  const [pagina, setPagina] = useState<Pagina | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargandoMas, setCargandoMas] = useState(false);
  const [borrar, setBorrar] = useState(false);

  const consulta = `/api/reviews/?id_tmdb=${idTmdb}&tipo=${tipo}&orden=${orden}${FILTROS[nota]}`;

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
  }, [consulta]);

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
  const filtrando = nota !== "0";
  const avatar = (id: number) => avatares.find((opcion) => opcion.id === id)?.src;
  const pildora =
    "inline-flex h-11 items-center gap-2 rounded-full pr-1 pl-3.5 text-sm whitespace-nowrap text-fg-3 shadow-[inset_0_0_0_1px_var(--line)]";
  const selector =
    "h-9 cursor-pointer rounded-full border-0 bg-raised-2 px-2.5 text-sm font-semibold text-foreground focus-visible:outline-2 focus-visible:outline-ring";

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
                className="inline-flex h-10 cursor-pointer items-center gap-1.5 rounded-lg px-3 text-sm font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
              >
                <Pencil aria-hidden="true" className="size-4" />
                {t("common.actions.edit")}
              </button>
              <button
                type="button"
                onClick={() => setBorrar(true)}
                className="inline-flex h-10 cursor-pointer items-center gap-1.5 rounded-lg px-3 text-sm font-semibold text-destructive focus-visible:outline-2 focus-visible:outline-ring"
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
            {pagina && (
              <h3 aria-live="polite" className="text-fg-2 tabular-nums">
                {filtrando
                  ? t("title.reviews.displayedCount", {
                      shownCount: formats.number(pagina.total),
                      totalCount: formats.number(pagina.total_comunidad),
                    })
                  : t("title.reviews.communityCount", {
                      count: formats.number(pagina.total_comunidad),
                    })}
              </h3>
            )}
            {filtrando && (
              <button
                type="button"
                onClick={() => {
                  setNota("0");
                  setOrden("fecha-desc");
                }}
                className="h-9 cursor-pointer px-1 text-sm font-semibold text-fg-2 underline underline-offset-[3px] hover:text-foreground"
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
                onChange={(event) => setOrden(event.target.value)}
                className={selector}
              >
                <option value="fecha-desc">{t("common.sort.newest")}</option>
                <option value="fecha-asc">{t("common.sort.oldest")}</option>
                <option value="nota-desc">{t("common.sort.highestRating")}</option>
                <option value="nota-asc">{t("common.sort.lowestRating")}</option>
              </select>
            </label>
            <label className={pildora}>
              {t("common.rating.label")}
              <select
                value={nota}
                onChange={(event) => setNota(event.target.value)}
                className={selector}
              >
                <option value="0">{t("common.filters.anyRating")}</option>
                <option value="9+">{t("common.filters.ratingAtLeastNine")}</option>
                <option value="8+">{t("common.filters.ratingAtLeastEight")}</option>
                <option value="7+">{t("common.filters.ratingAtLeastSeven")}</option>
                <option value="6+">{t("common.filters.ratingAtLeastSix")}</option>
                <option value="5+">{t("common.filters.ratingAtLeastFive")}</option>
                <option value="m5">{t("common.filters.ratingBelowFive")}</option>
              </select>
            </label>
          </div>
        </div>

        {error && (
          <p role="alert" className="py-6 text-fg-2">
            {error}
          </p>
        )}
        {!pagina &&
          !error &&
          [0, 1, 2].map((i) => (
            <div
              key={i}
              aria-hidden="true"
              className="grid grid-cols-[40px_minmax(0,1fr)] gap-4 border-t border-line py-[22px]"
            >
              <span className="size-10 animate-pulse rounded-full bg-raised motion-reduce:animate-none" />
              <span className="flex flex-col gap-2.5 pt-1">
                <span className="h-4 w-48 animate-pulse rounded bg-raised motion-reduce:animate-none" />
                <span className="h-4 w-full animate-pulse rounded bg-raised motion-reduce:animate-none" />
                <span className="h-4 w-2/3 animate-pulse rounded bg-raised motion-reduce:animate-none" />
              </span>
            </div>
          ))}
        {pagina?.results.map((resena) => (
          <article
            key={`${resena.nombre_usuario}-${resena.fecha}`}
            className="grid grid-cols-[40px_minmax(0,1fr)] gap-4 border-t border-line py-[22px]"
          >
            {avatar(resena.avatar_id) ? (
              <Image
                unoptimized
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
                {resena.nombre_usuario.charAt(0)}
              </span>
            )}
            <div className="flex min-w-0 flex-col gap-1.5">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5">
                <span className="font-semibold">@{resena.nombre_usuario}</span>
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
        {pagina && pagina.total_comunidad > 0 && pagina.results.length === 0 && (
          <div
            role="status"
            className="flex flex-col items-start gap-2 border-t border-line py-6 text-fg-2"
          >
            <p>{t("title.reviews.filteredEmpty")}</p>
          </div>
        )}
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
