"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

export type Pedido<T> =
  | { status: "idle" | "loading"; data: null; error: null }
  | { status: "ok"; data: T; error: null }
  | { status: "error"; data: null; error: unknown };

/**
 * Respuestas públicas del catálogo ya recibidas en esta visita. Volver a una
 * opción del selector no repite el pedido; lo que falló no se guarda.
 */
const cache = new Map<string, unknown>();

export function limpiarCacheCatalogo() {
  cache.clear();
}

/**
 * Pide `path` a la API (con `apiFetch`) y devuelve en qué estado está. `null`
 * no pide nada. `intento` distinto vuelve a pedir lo que falló. Con
 * `cachear: false` siempre pide (Recomendado depende de lo que el usuario
 * califique después).
 */
export function useCatalog<T>(path: string | null, intento = 0, cachear = true): Pedido<T> {
  const clave = path === null ? null : `${path}#${intento}`;
  const [resultados, setResultados] = useState<Record<string, { data?: T; error?: unknown }>>({});
  const guardado = cachear && path !== null && cache.has(path);

  useEffect(() => {
    if (path === null || clave === null || (cachear && cache.has(path))) return;
    let vigente = true;
    apiFetch<T>(path).then(
      (data) => {
        if (cachear) cache.set(path, data);
        if (vigente) setResultados((anteriores) => ({ ...anteriores, [clave]: { data } }));
      },
      (error: unknown) => {
        if (vigente) setResultados((anteriores) => ({ ...anteriores, [clave]: { error } }));
      }
    );
    return () => {
      vigente = false;
    };
  }, [path, clave, cachear]);

  if (path === null || clave === null) return { status: "idle", data: null, error: null };
  if (guardado) return { status: "ok", data: cache.get(path) as T, error: null };
  const resultado = resultados[clave];
  if (!resultado) return { status: "loading", data: null, error: null };
  return resultado.error !== undefined
    ? { status: "error", data: null, error: resultado.error }
    : { status: "ok", data: resultado.data as T, error: null };
}

export type Paginas<T> = {
  /** Las páginas ya llegadas, en orden, hasta la primera que falta. */
  paginas: T[];
  /** `loading` hasta que llega la primera; `error` si alguna falló. */
  status: "loading" | "ok" | "error";
  error: unknown;
  /** Hay páginas pedidas que todavía no llegaron (las siguientes a la primera). */
  cargandoMas: boolean;
};

/**
 * Varias páginas de una misma consulta (Buscar al bajar, C-06). Comparte la
 * caché con `useCatalog`: volver desde la ficha muestra al instante todo lo
 * que ya se había cargado, y el navegador puede devolver el scroll a su lugar.
 */
export function useCatalogPaginas<T>(paths: string[], intento = 0): Paginas<T> {
  const clave = `${paths.join("|")}#${intento}`;
  const [, setLlegadas] = useState(0);
  const [fallo, setFallo] = useState<{ clave: string; error: unknown } | null>(null);

  useEffect(() => {
    let vigente = true;
    for (const path of paths) {
      if (cache.has(path)) continue;
      apiFetch(path).then(
        (data) => {
          cache.set(path, data);
          if (vigente) setLlegadas((anterior) => anterior + 1);
        },
        (error: unknown) => {
          if (vigente) setFallo({ clave, error });
        }
      );
    }
    return () => {
      vigente = false;
    };
    // `clave` resume `paths` e `intento`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave]);

  const llegadas: T[] = [];
  for (const path of paths) {
    if (!cache.has(path)) break;
    llegadas.push(cache.get(path) as T);
  }
  const error = fallo?.clave === clave ? fallo.error : null;
  return {
    paginas: llegadas,
    status: error !== null ? "error" : llegadas.length === 0 ? "loading" : "ok",
    error,
    cargandoMas: llegadas.length > 0 && llegadas.length < paths.length && error === null,
  };
}
