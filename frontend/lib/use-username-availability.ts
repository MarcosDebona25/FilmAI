"use client";

import { useEffect, useRef, useState } from "react";

import { currentLocale } from "@/i18n/client";
import { apiUrl } from "@/lib/api";

export type UsernameAvailability = "idle" | "checking" | "disponible" | "ocupado" | "reservado";

/**
 * Disponibilidad del nombre de usuario en vivo, con debounce (registro y alta
 * con Google). Solo consulta cuando el valor pasa la validación local; un
 * error de red o un 429 (Too Many Requests) vuelve a «idle», nunca a «ocupado».
 * `marcarOcupado` deja el estado en «ocupado» cuando el backend lo rechaza al
 * enviar el formulario. «reservado» es un nombre que se confunde con una cuenta
 * del equipo (issue #137): se muestra el mismo error que al enviarlo.
 */
export function useUsernameAvailability(valor: string, valido: boolean) {
  const [estado, setEstado] = useState<UsernameAvailability>("idle");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    const username = valor.trim();
    clearTimeout(debounceRef.current);
    if (!username || !valido) {
      setEstado("idle");
      return;
    }
    setEstado("checking");
    const controller = new AbortController();
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(
          apiUrl(`/api/auth/username-available/?username=${encodeURIComponent(username)}`),
          { signal: controller.signal, headers: { "Accept-Language": currentLocale() } }
        );
        if (!res.ok) {
          setEstado("idle");
          return;
        }
        const data: { disponible?: boolean; motivo?: string } = await res.json();
        setEstado(
          data.disponible ? "disponible" : data.motivo === "reservado" ? "reservado" : "ocupado"
        );
      } catch {
        if (!controller.signal.aborted) setEstado("idle");
      }
    }, 400);
    return () => {
      clearTimeout(debounceRef.current);
      controller.abort();
    };
  }, [valor, valido]);

  return { estado, marcarOcupado: () => setEstado("ocupado") };
}
