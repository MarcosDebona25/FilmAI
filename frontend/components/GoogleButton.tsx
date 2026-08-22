"use client";

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
};

type GoogleCredentialResponse = {
  credential?: string;
};

export function GoogleButton({ onSuccess, onError }: GoogleButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const callbacksRef = useRef({ onSuccess, onError });
  callbacksRef.current = { onSuccess, onError };

  useEffect(() => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId || !containerRef.current) return;

    const scriptId = "google-identity-services";

    function render() {
      window.google?.accounts?.id?.initialize({
        client_id: clientId,
        callback: (response: GoogleCredentialResponse) => {
          if (response?.credential) {
            callbacksRef.current.onSuccess(response.credential);
          } else {
            callbacksRef.current.onError?.("No se pudo obtener la credencial de Google.");
          }
        },
      });
      window.google?.accounts?.id?.renderButton(containerRef.current, {
        theme: "filled_black",
        size: "large",
        width: 320,
      });
    }

    if (document.getElementById(scriptId)) {
      if (window.google?.accounts?.id) render();
      return;
    }

    const script = document.createElement("script");
    script.id = scriptId;
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = render;
    document.head.appendChild(script);
  }, []);

  if (!process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID) {
    return (
      <p className="text-xs text-muted-foreground">
        Configurá <code>NEXT_PUBLIC_GOOGLE_CLIENT_ID</code> para habilitar Google.
      </p>
    );
  }

  return <div ref={containerRef} aria-label="Continuar con Google" />;
}
