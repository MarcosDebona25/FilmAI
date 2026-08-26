"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api";

type Estado = "cargando" | "ok" | "ya_confirmada" | "expirado" | "error";

export default function ConfirmarCorreoPage() {
  const params = useParams<{ key: string }>();
  const [estado, setEstado] = useState<Estado>("cargando");

  useEffect(() => {
    const key = params?.key;
    if (!key) {
      setEstado("error");
      return;
    }
    apiFetch("/api/auth/registration/verify-email/", {
      method: "POST",
      body: { key },
    })
      .then(() => setEstado("ok"))
      .catch((err: unknown) => {
        const codigo =
          err instanceof ApiError && err.details && typeof err.details === "object"
            ? (err.details as { codigo?: unknown }).codigo
            : undefined;
        if (codigo === "ya_confirmada") setEstado("ya_confirmada");
        else if (codigo === "expirado") setEstado("expirado");
        else setEstado("error");
      });
  }, [params]);

  function volverAlRegistro() {
    window.location.href = "/register";
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center">
        <p className="mb-4 text-2xl font-bold text-foreground">FilmAI</p>

        {estado === "cargando" && <p className="text-muted-foreground">Confirmando su cuenta…</p>}

        {estado === "ok" && (
          <>
            <h1 className="mb-3 text-2xl font-bold text-foreground">Cuenta confirmada</h1>
            <p className="mb-6 text-sm text-muted-foreground">
              Su cuenta quedó activa. Ya puede iniciar sesión.
            </p>
            <Link href="/login" className="text-primary hover:underline">
              Ir a iniciar sesión
            </Link>
          </>
        )}

        {estado === "ya_confirmada" && (
          <>
            <h1 className="mb-3 text-2xl font-bold text-foreground">Cuenta ya confirmada</h1>
            <p className="mb-6 text-sm text-muted-foreground">
              Esta dirección ya estaba confirmada. Puede iniciar sesión directamente.
            </p>
            <Link href="/login" className="text-primary hover:underline">
              Ir a iniciar sesión
            </Link>
          </>
        )}

        {estado === "expirado" && (
          <>
            <h1 className="mb-3 text-2xl font-bold text-foreground">El enlace expiró</h1>
            <p className="mb-6 text-sm text-muted-foreground">
              Los enlaces de confirmación son válidos durante 24 horas. Puede pedir uno nuevo desde
              la pantalla de registro con el botón &quot;Reenviar correo&quot;.
            </p>
            <button
              type="button"
              onClick={volverAlRegistro}
              className="text-primary hover:underline"
            >
              Volver al registro
            </button>
          </>
        )}

        {estado === "error" && (
          <>
            <h1 className="mb-3 text-2xl font-bold text-foreground">No se pudo confirmar</h1>
            <p className="mb-6 text-sm text-muted-foreground">El enlace es inválido.</p>
            <Link href="/login" className="text-primary hover:underline">
              Volver a iniciar sesión
            </Link>
          </>
        )}
      </div>
    </main>
  );
}
