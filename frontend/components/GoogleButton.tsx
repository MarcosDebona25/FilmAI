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
};

type GoogleCredentialResponse = {
  credential?: string;
};

export function GoogleButton({ onSuccess, onError, text = "continue_with" }: GoogleButtonProps) {
  const locale = useLocale();
  const t = useTranslations("errors.codes");
  const auth = useTranslations("auth.google");
  const containerRef = useRef<HTMLDivElement>(null);
  const callbacksRef = useRef({ onSuccess, onError, text, locale });
  callbacksRef.current = { onSuccess, onError, text, locale };

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
      window.google?.accounts?.id?.renderButton(container, {
        locale: callbacksRef.current.locale,
        theme: "filled_black",
        size: "large",
        width: 320,
        text: callbacksRef.current.text,
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

  return <div ref={containerRef} aria-label={auth("continue")} />;
}
