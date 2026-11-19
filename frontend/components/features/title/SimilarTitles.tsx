"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { MediaRow } from "@/components/features/MediaRow";
import type { MediaType } from "@/lib/catalog";
import { sugerenciaATitulo, type Sugerencia } from "@/lib/lists";
import { useCatalog } from "@/lib/use-catalog";

/** Distancia al viewport a la que se piden los parecidos (canvas, sección 14). */
const ANTICIPO = "400px";

/**
 * «More like {title}» de la ficha (canvas, sección 14): la misma fila del
 * Inicio con los títulos de `GET /api/catalogo/{tipo}/{id}/similar/`.
 *
 * - No pide nada con el detalle: espera a que un centinela (un `div` sin alto
 *   en el lugar de la fila) esté a 400 px de entrar al viewport. Quien no baja
 *   no paga el pedido.
 * - Sin resultados o con error no se dibuja nada: ni título ni mensaje.
 */
export function SimilarTitles({
  tipo,
  id,
  titulo,
  from,
}: {
  tipo: MediaType;
  id: number;
  /** Título de la ficha, para el encabezado. */
  titulo: string;
  /** Origen de la ficha actual (`?from=`): las tarjetas lo conservan. */
  from?: string;
}) {
  const t = useTranslations("title.similar");
  const centinela = useRef<HTMLDivElement>(null);
  const [cerca, setCerca] = useState(false);

  useEffect(() => {
    const nodo = centinela.current;
    if (cerca || !nodo || typeof IntersectionObserver === "undefined") return;
    // `IntersectionObserver` avisa cuando un elemento entra al viewport;
    // `rootMargin` agranda ese viewport hacia abajo para avisar antes.
    const observador = new IntersectionObserver(
      (entradas) => {
        if (entradas.some((entrada) => entrada.isIntersecting)) setCerca(true);
      },
      { rootMargin: `0px 0px ${ANTICIPO} 0px` }
    );
    observador.observe(nodo);
    return () => observador.disconnect();
  }, [cerca]);

  // Sin la caché de la visita: con sesión la respuesta no trae lo de «Vistas»,
  // que cambia al calificar o al entrar otra cuenta.
  const pedido = useCatalog<{ results: Sugerencia[] }>(
    cerca ? `/api/catalogo/${tipo}/${id}/similar/` : null,
    0,
    false
  );

  if (!cerca)
    // El margen negativo cancela el `gap` de la columna de la ficha (4rem y
    // 6rem desde `md`): el centinela no ocupa lugar ni separa las secciones.
    return <div ref={centinela} aria-hidden="true" className="-mb-16 h-0 md:-mb-24" />;
  if (pedido.status === "error") return null;
  // Una respuesta sin `results` cuenta como vacía: la fila es secundaria y no
  // puede romper la ficha.
  const resultados = pedido.data?.results;
  const titulos = Array.isArray(resultados) ? resultados.map(sugerenciaATitulo) : [];
  if (pedido.status === "ok" && titulos.length === 0) return null;

  return (
    // En celular la fila del Inicio va de borde a borde y trae su propio
    // margen: se sale del `page-container` de la ficha (1.25rem por lado).
    <div className="max-md:-mx-5">
      <MediaRow
        title={t("title", { title: titulo })}
        items={titulos}
        showType
        from={from}
        loading={pedido.status === "loading"}
      />
    </div>
  );
}
