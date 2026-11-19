"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import {
  bloquearAccionesDelAviso,
  cerrarAvisoEstado,
  mostrarAvisoEstado,
} from "@/components/features/title/StatusToast";

/**
 * Cuánto puede tardar un guardado antes de avisar «Saving…». Por debajo de ese
 * umbral no aparece nada: el toast de siempre lo reemplaza sin parpadeo.
 */
export const MS_ANTES_DE_AVISAR = 200;

/**
 * El bloqueo mientras se guarda, compartido por la ficha y la lista Watching.
 *
 * Mientras hay un guardado en curso, las acciones se deshabilitan desde el
 * primer toque (el hook expone `guardando`) y el aviso visible bloquea su Undo.
 * Si el servidor tarda más de `MS_ANTES_DE_AVISAR`, aparece el toast «Saving…»
 * con spinner; al terminar se cierra, y quien llama muestra el toast de
 * siempre. Un solo aviso de estado a la vez: el de guardado reemplaza al
 * anterior, y el Undo viejo se pierde (decisión del 19/11/2026).
 */
export function useAvisoGuardado() {
  const t = useTranslations();
  const [guardando, setGuardando] = useState(false);
  const temporizador = useRef<number | null>(null);
  const avisoVisible = useRef(false);

  const limpiarTemporizador = useCallback(() => {
    if (temporizador.current === null) return;
    window.clearTimeout(temporizador.current);
    temporizador.current = null;
  }, []);

  const empezar = useCallback(() => {
    setGuardando(true);
    bloquearAccionesDelAviso(true);
    limpiarTemporizador();
    avisoVisible.current = false;
    temporizador.current = window.setTimeout(() => {
      temporizador.current = null;
      avisoVisible.current = true;
      mostrarAvisoEstado({ texto: t("title.status.saving"), cargando: true });
    }, MS_ANTES_DE_AVISAR);
  }, [limpiarTemporizador, t]);

  const terminar = useCallback(() => {
    setGuardando(false);
    bloquearAccionesDelAviso(false);
    limpiarTemporizador();
    if (!avisoVisible.current) return;
    avisoVisible.current = false;
    cerrarAvisoEstado();
  }, [limpiarTemporizador]);

  // Al desmontar (salir de la ficha o de la lista) no queda un temporizador
  // suelto ni el aviso bloqueado para la pantalla siguiente.
  useEffect(() => {
    return () => {
      limpiarTemporizador();
      bloquearAccionesDelAviso(false);
    };
  }, [limpiarTemporizador]);

  return { guardando, empezar, terminar };
}
