"use client";
import { routes } from "@/lib/routes";

import { useRouter } from "next/navigation";

import { marcarGooglePendiente } from "@/lib/google-auth";

/** Botón estilizado de Google que inicia el flujo de registro con Google.
 *
 * A diferencia de `GoogleButton` (que abre el popup de Google), este solo
 * marca el flujo pendiente y navega a /complete-signup, donde se pide el
 * id_token junto con los datos faltantes (un único toque de Google).
 */
export function GoogleLinkButton({ label = "Crear cuenta con Google" }: { label?: string }) {
  const router = useRouter();

  return (
    <button
      type="button"
      onClick={() => {
        marcarGooglePendiente();
        router.push(routes.completeSignup);
      }}
      className="flex h-11 w-full max-w-xs items-center justify-center gap-3 rounded-md bg-[#1a1a1a] px-4 text-sm font-medium text-white shadow-sm transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label={label}
    >
      <GoogleLogo />
      {label}
    </button>
  );
}

function GoogleLogo() {
  return (
    <svg className="size-5" viewBox="0 0 48 48" aria-hidden="true">
      <path
        fill="#EA4335"
        d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
      />
      <path
        fill="#4285F4"
        d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
      />
      <path
        fill="#FBBC05"
        d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
      />
      <path
        fill="#34A853"
        d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
      />
    </svg>
  );
}
