"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

/* eslint-disable @typescript-eslint/no-explicit-any */
declare global {
  interface Window {
    google?: any;
  }
}
/* eslint-enable @typescript-eslint/no-explicit-any */

type GoogleButtonProps = {
  onSuccess: (idToken: string) => void;
  onError?: (message: string) => void;
  /** Texto del botón oficial de Google (GIS). El default es "continue_with". */
  text?: "signin_with" | "signup_with" | "continue_with";
  /** Tema de GIS: `outline` es el botón blanco del alta con Google. */
  theme?: "filled_black" | "outline";
  /** Ocupa el ancho del contenedor (GIS acepta hasta 400 px). */
  fullWidth?: boolean;
};

type GoogleCredentialResponse = {
  credential?: string;
};

export function GoogleButton({
  onSuccess,
  onError,
  text = "continue_with",
  theme = "filled_black",
  fullWidth = false,
}: GoogleButtonProps) {
  const locale = useLocale();
  const t = useTranslations("errors.codes");
  const auth = useTranslations("auth.google");
  const containerRef = useRef<HTMLDivElement>(null);
  const callbacksRef = useRef({ onSuccess, onError, text, locale, theme, fullWidth });
  callbacksRef.current = { onSuccess, onError, text, locale, theme, fullWidth };

  useEffect(() => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId || !containerRef.current) return;

    const scriptId = "google-identity-services";

    function render() {
      const container = containerRef.current;
      if (!container || !window.google?.accounts?.id) return;
      container.replaceChildren();
      window.google?.accounts?.id?.initialize({
        client_id: clientId,
        callback: (response: GoogleCredentialResponse) => {
          if (response?.credential) {
            callbacksRef.current.onSuccess(response.credential);
          } else {
            callbacksRef.current.onError?.(t("google_authentication_failed"));
          }
        },
      });
      const opciones = callbacksRef.current;
      window.google?.accounts?.id?.renderButton(container, {
        locale: opciones.locale,
        theme: opciones.theme,
        size: "large",
        width: opciones.fullWidth ? Math.min(400, container.clientWidth || 320) : 320,
        text: opciones.text,
      });
    }

    if (window.google?.accounts?.id) {
      render();
      return;
    }
    let script = document.getElementById(scriptId) as HTMLScriptElement | null;
    if (!script) {
      script = document.createElement("script");
      script.id = scriptId;
      script.src = `https://accounts.google.com/gsi/client?hl=${locale}`;
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }
    script.addEventListener("load", render);
    return () => script.removeEventListener("load", render);
  }, [locale, t]);

  if (!process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID) {
    return null;
  }

  return (
    <div
      ref={containerRef}
      aria-label={auth("continue")}
      // El alto reservado (botón `large` de GIS) evita que el contenido salte al dibujarlo.
      className={fullWidth ? "flex min-h-10 w-full justify-center" : undefined}
    />
  );
}
