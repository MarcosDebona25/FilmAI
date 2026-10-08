"use client";
import { routes } from "@/lib/routes";

import { useTranslations } from "next-intl";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api";

type Estado = "cargando" | "ok" | "ya_confirmada" | "expirado" | "error";

export default function ConfirmarCorreoPage() {
  const t = useTranslations("legacy.confirmation");

  const params = useParams<{ key: string }>();
  const [estado, setEstado] = useState<Estado>("cargando");

  useEffect(() => {
    const rawKey = params?.key;
    if (!rawKey) {
      setEstado("error");
      return;
    }
    // useParams() devuelve valores URL-encoded; la key HMAC contiene ":"
    // que llega como "%3A" y rompe signing.loads en el backend.
    let key: string;
    try {
      key = decodeURIComponent(rawKey);
    } catch {
      // Un "%" suelto hace lanzar URIError: es un enlace inválido, no un
      // motivo para quedar en "cargando".
      setEstado("error");
      return;
    }
    apiFetch("/api/auth/registration/verify-email/", {
      method: "POST",
      body: { key },
    })
      .then(() => setEstado("ok"))
      .catch((err: unknown) => {
        const codigo = err instanceof ApiError ? err.code : undefined;
        if (codigo === "already_confirmed") setEstado("ya_confirmada");
        else if (codigo === "link_expired") setEstado("expirado");
        else setEstado("error");
      });
  }, [params]);

  return (
    <main id="contenido" className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center">
        <p className="mb-4 text-2xl font-bold text-foreground">FilmAI</p>

        {estado === "cargando" && (
          <p role="status" className="text-foreground/75">
            {t("loading")}
          </p>
        )}

        {estado === "ok" && (
          <>
            <h1 className="mb-3 text-2xl font-bold text-foreground">{t("successTitle")}</h1>
            <p className="mb-6 text-sm text-foreground/75">{t("successDescription")}</p>
            <Link href={routes.login} className="text-primary hover:underline">
              {t("goToLogin")}
            </Link>
          </>
        )}

        {estado === "ya_confirmada" && (
          <>
            <h1 className="mb-3 text-2xl font-bold text-foreground">{t("alreadyTitle")}</h1>
            <p className="mb-6 text-sm text-foreground/75">{t("alreadyDescription")}</p>
            <Link href={routes.login} className="text-primary hover:underline">
              {t("goToLogin")}
            </Link>
          </>
        )}

        {estado === "expirado" && (
          <>
            <h1 className="mb-3 text-2xl font-bold text-foreground">{t("expiredTitle")}</h1>
            <p className="mb-6 text-sm text-foreground/75">{t("expiredDescription")}</p>
            <Link href={routes.register} className="text-primary hover:underline">
              {t("backToRegister")}
            </Link>
          </>
        )}

        {estado === "error" && (
          <>
            <h1 className="mb-3 text-2xl font-bold text-foreground">{t("errorTitle")}</h1>
            <p className="mb-6 text-sm text-foreground/75">{t("errorDescription")}</p>
            <Link href={routes.login} className="text-primary hover:underline">
              {t("backToLogin")}
            </Link>
          </>
        )}
      </div>
    </main>
  );
}
