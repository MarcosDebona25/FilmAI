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
