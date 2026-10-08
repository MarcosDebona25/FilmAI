"use client";

import { useTranslations } from "next-intl";
import { useFormats } from "@/lib/format";
import Image from "next/image";
import { Film, Star, MessageSquareDashed } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { posterUrl, type MiResena } from "@/lib/reviews";

export function ReviewCard({
  item,
  onAction,
}: {
  item: MiResena;
  onAction: (action: "edit" | "text" | "rating") => void;
}) {
  const formats = useFormats();
  const content = useTranslations("common.content");
  const [expanded, setExpanded] = useState(false);
  const [truncated, setTruncated] = useState(false);
  const textRef = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    const text = textRef.current;
    if (!text) return;
    const measure = () => {
      const lineHeight = Number.parseFloat(getComputedStyle(text).lineHeight);
      setTruncated(Boolean(item.texto) && text.scrollHeight > lineHeight * 3 + 1);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(text);
    return () => observer.disconnect();
  }, [item.texto]);
  const [failed, setFailed] = useState<string | null>(null);
  const src = posterUrl(item.poster);
  return (
    <article
      aria-label={`Calificación de ${item.titulo}`}
      className="rounded-xl border border-border bg-card p-5"
      style={{ contentVisibility: "auto", containIntrinsicSize: "auto 280px" }}
    >
      <div className="grid grid-cols-[56px_minmax(0,1fr)] gap-x-4 gap-y-3 sm:grid-cols-[80px_minmax(0,1fr)]">
        <div className="relative h-[84px] w-14 overflow-hidden rounded-lg bg-secondary sm:row-span-2 sm:h-[120px] sm:w-20">
          {src && failed !== src ? (
            <Image
              unoptimized
              src={src}
              alt={`Póster de ${item.titulo}`}
              fill
              sizes="(min-width: 640px) 80px, 56px"
              className="object-cover"
              onError={() => setFailed(src)}
            />
          ) : (
            <span
              role="img"
              aria-label={`Sin póster de ${item.titulo}`}
              className="flex h-full items-center justify-center"
            >
              <Film aria-hidden="true" className="size-7" />
            </span>
          )}
        </div>
        <div className="min-w-0">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2">
            <h2
              lang={item.campos_en_ingles?.includes("titulo") ? "en" : undefined}
              className="break-words text-lg font-semibold"
            >
              {item.titulo}
            </h2>
            <time
              dateTime={item.fecha}
              className="pt-1 text-right text-xs tabular-nums text-foreground/75"
            >
              {formats.date(item.fecha)}
            </time>
          </div>
          <p className="text-sm text-foreground/75">
            {content(item.tipo === "movie" ? "movie" : "tvShow")}
          </p>
          <p className="mt-1 text-sm tabular-nums">
            <span
              aria-label={`Calificación: ${item.valor} de 10`}
              className="inline-flex items-center gap-1 font-semibold"
            >
              <Star aria-hidden="true" className="size-4 shrink-0 fill-current text-[#f5c518]" />
              {item.valor}/10
            </span>
          </p>
        </div>
        <div className="col-span-2 min-w-0 sm:col-span-1 sm:col-start-2">
          <p
            ref={textRef}
            role={item.texto ? undefined : "note"}
            className={
              item.texto
                ? `whitespace-pre-wrap break-words leading-6 ${expanded ? "" : "line-clamp-3"}`
                : "flex items-start gap-2 rounded-lg border border-dashed border-border bg-secondary/50 p-3 text-sm italic leading-6 text-foreground/75"
            }
          >
            {!item.texto && (
              <MessageSquareDashed aria-hidden="true" className="mt-1 size-4 shrink-0" />
            )}
            {item.texto || "Todavía no escribiste una reseña."}
          </p>
          {truncated && (
            <Button
              variant="link"
              className="min-h-11 px-0"
              aria-expanded={expanded}
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? "Leer menos" : "Leer más"}
            </Button>
          )}
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-3">
        <Button variant="secondary" className="min-h-11" onClick={() => onAction("edit")}>
          Editar
        </Button>
        {item.texto && (
          <Button variant="destructive" className="min-h-11" onClick={() => onAction("text")}>
            Eliminar reseña
          </Button>
        )}
        <Button variant="destructive" className="min-h-11" onClick={() => onAction("rating")}>
          Quitar calificación
        </Button>
      </div>
    </article>
  );
}
