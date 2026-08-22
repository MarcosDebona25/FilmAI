"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

type Estado = "cargando" | "ok" | "error";

export default function ConfirmarCorreoPage() {
  const params = useParams<{ key: string }>();
  const [estado, setEstado] = useState<Estado>("cargando");
  const [mensaje, setMensaje] = useState("");

  useEffect(() => {
    const key = params?.key;
    if (!key) {
      setEstado("error");
      setMensaje("Enlace inválido.");
      return;
    }
    apiFetch("/api/auth/registration/verify-email/", {
      method: "POST",
      body: { key },
      auth: false,
    })
      .then(() => setEstado("ok"))
      .catch(() => {
        setEstado("error");
        setMensaje("El enlace es inválido o ya expiró.");
      });
  }, [params]);

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center">
        {estado === "cargando" && <p className="text-muted-foreground">Confirmando tu cuenta…</p>}

        {estado === "ok" && (
          <>
            <h1 className="mb-3 text-2xl font-bold text-foreground">Cuenta confirmada</h1>
            <p className="mb-6 text-sm text-muted-foreground">
              Tu cuenta quedó activa. Ya podés iniciar sesión.
            </p>
            <Link href="/login" className="text-primary hover:underline">
              Ir a iniciar sesión
            </Link>
          </>
        )}

        {estado === "error" && (
          <>
            <h1 className="mb-3 text-2xl font-bold text-foreground">No se pudo confirmar</h1>
            <p className="mb-6 text-sm text-muted-foreground">{mensaje}</p>
            <Link href="/login" className="text-primary hover:underline">
              Volver a iniciar sesión
            </Link>
          </>
        )}
      </div>
    </main>
  );
}
