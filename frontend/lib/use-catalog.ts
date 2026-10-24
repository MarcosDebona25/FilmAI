"use client";

import { useEffect, useState } from "react";
import { useLocale } from "next-intl";

import { apiFetch } from "@/lib/api";

export type Pedido<T> =
  | { status: "idle" | "loading"; data: null; error: null }
  | { status: "ok"; data: T; error: null }
  | { status: "error"; data: null; error: unknown };

/**
 * Respuestas públicas del catálogo ya recibidas en esta visita. Volver a una
 * opción del selector no repite el pedido; lo que falló no se guarda.
 *
 * La clave lleva el idioma (`es|/api/…`): la API traduce títulos y géneros
 * según `Accept-Language`, y el idioma puede cambiar sin recargar la página
 * (el de la cuenta al iniciar sesión, o el selector). Sin él, una fila quedaba
 * con los títulos del idioma anterior (16/10/2026).
 */
const cache = new Map<string, unknown>();
const claveCache = (idioma: string, path: string) => `${idioma}|${path}`;

export function limpiarCacheCatalogo() {
  cache.clear();
}

/**
 * Pide `path` a la API (con `apiFetch`) y devuelve en qué estado está. `null`
 * no pide nada. `intento` distinto vuelve a pedir lo que falló. Con
 * `cachear: false` siempre pide (Recomendado depende de lo que el usuario
 * califique después).
 *
 * `inicial` es la respuesta que ya trajo el servidor de Next (el Hero del
 * Inicio, 24/10/2026): con ella no se pide nada y el dato está desde el primer
 * render. Quien la pasa se asegura de que sea del idioma actual.
 */
export function useCatalog<T>(
  path: string | null,
  intento = 0,
  cachear = true,
  inicial?: T
): Pedido<T> {
  const idioma = useLocale();
  const clave = path === null ? null : `${claveCache(idioma, path)}#${intento}`;
  const [resultados, setResultados] = useState<Record<string, { data?: T; error?: unknown }>>({});
  const enCache = path === null ? null : claveCache(idioma, path);
  const guardado = cachear && enCache !== null && cache.has(enCache);
  const conInicial = inicial !== undefined && path !== null;

  useEffect(() => {
    if (path === null || clave === null || enCache === null || (cachear && cache.has(enCache)))
      return;
    if (conInicial) {
      // Queda en la caché de la visita, como si la hubiera pedido el navegador.
      if (cachear) cache.set(enCache, inicial);
      return;
    }
    let vigente = true;
    apiFetch<T>(path).then(
      (data) => {
        if (cachear) cache.set(enCache, data);
        if (vigente) setResultados((anteriores) => ({ ...anteriores, [clave]: { data } }));
      },
      (error: unknown) => {
        if (vigente) setResultados((anteriores) => ({ ...anteriores, [clave]: { error } }));
      }
    );
    return () => {
      vigente = false;
    };
  }, [path, clave, enCache, cachear, conInicial, inicial]);

  if (path === null || clave === null) return { status: "idle", data: null, error: null };
  if (guardado) return { status: "ok", data: cache.get(enCache) as T, error: null };
  if (conInicial) return { status: "ok", data: inicial, error: null };
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
  const idioma = useLocale();
  const clave = `${idioma}|${paths.join("|")}#${intento}`;
  const [, setLlegadas] = useState(0);
  const [fallo, setFallo] = useState<{ clave: string; error: unknown } | null>(null);

  useEffect(() => {
    let vigente = true;
    for (const path of paths) {
      if (cache.has(claveCache(idioma, path))) continue;
      apiFetch(path).then(
        (data) => {
          cache.set(claveCache(idioma, path), data);
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
    // `clave` resume el idioma, `paths` e `intento`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave]);

  const llegadas: T[] = [];
  for (const path of paths) {
    if (!cache.has(claveCache(idioma, path))) break;
    llegadas.push(cache.get(claveCache(idioma, path)) as T);
  }
  const error = fallo?.clave === clave ? fallo.error : null;
  return {
    paginas: llegadas,
    status: error !== null ? "error" : llegadas.length === 0 ? "loading" : "ok",
    error,
    cargandoMas: llegadas.length > 0 && llegadas.length < paths.length && error === null,
  };
}
