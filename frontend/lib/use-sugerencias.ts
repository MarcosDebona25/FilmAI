"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import {
  ESPERA_SUGERENCIAS_MS,
  MIN_CARACTERES,
  pedirSugerencias,
  sugerenciasEnCache,
  type Sugerencia,
} from "@/lib/sugerencias";

/**
 * Las sugerencias del texto de un campo. Lo usan la lupa de la navbar y el
 * campo de Buscar: así los dos piden igual (14/11/2026).
 *
 * Es un «hook»: una función de React que guarda estado y efectos y se reutiliza
 * entre componentes (parecido a una clase de servicio que se inyecta, pero que
 * vive dentro del ciclo de render).
 *
 * Los pedidos: 250 ms después de la última tecla y desde 2 caracteres, cada
 * pedido cancela al anterior, y una respuesta que llega tarde (de un texto que
 * ya no es el del campo) se descarta. Lo ya visto sale de una caché de la visita.
 *
 * - `activo` apaga todo (la lupa cerrada no pide nada).
 * - `deTexto` es el texto al que responde `sugerencias`: mientras llega la
 *   respuesta nueva se conserva la vieja, y quien la usa para otra cosa (el
 *   aviso de Buscar) tiene que comprobar que sigue siendo la del texto actual.
 */
export function useSugerencias(texto: string, activo: boolean) {
  const t = useTranslations("nav.search");
  const idioma = useLocale();
  const recortado = texto.trim();
  const sugiere = recortado.length >= MIN_CARACTERES;

  const [respuesta, setRespuesta] = useState<{ lista: Sugerencia[]; deTexto: string } | null>(null);
  const [cargando, setCargando] = useState(false);
  const [anuncio, setAnuncio] = useState("");

  useEffect(() => {
    if (!activo) return;
    if (!sugiere) {
      setRespuesta(null);
      setCargando(false);
      return;
    }
    const guardadas = sugerenciasEnCache(idioma, recortado);
    if (guardadas) {
      setRespuesta({ lista: guardadas, deTexto: recortado });
      setCargando(false);
      setAnuncio(t("count", { count: guardadas.length }));
      return;
    }
    const control = new AbortController();
    setCargando(true);
    const espera = window.setTimeout(() => {
      pedirSugerencias(recortado, idioma, control.signal).then(
        (lista) => {
          if (control.signal.aborted) return;
          setRespuesta({ lista, deTexto: recortado });
          setCargando(false);
          setAnuncio(t("count", { count: lista.length }));
        },
        () => {
          // 429 (Too Many Requests), 503 (Service Unavailable)…: la lista se cierra
          // sin avisar; Enter sigue buscando, y esa búsqueda muestra su propio error.
          if (control.signal.aborted) return;
          setRespuesta(null);
          setCargando(false);
        }
      );
    }, ESPERA_SUGERENCIAS_MS);
    // El `return` cancela el pedido y la espera del texto anterior: ese es el «descartar lo viejo».
    return () => {
      window.clearTimeout(espera);
      control.abort();
    };
    // `t` cambia en cada render y solo se usa para el aviso.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activo, sugiere, recortado, idioma]);

  return {
    sugiere,
    sugerencias: respuesta?.lista ?? null,
    deTexto: respuesta?.deTexto ?? null,
    cargando,
    /** Texto para la región `aria-live`: «5 suggestions». */
    anuncio,
    /** Tira lo recibido (al cerrar el campo). */
    descartar() {
      setRespuesta(null);
      setCargando(false);
    },
  };
}
