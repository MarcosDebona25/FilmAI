"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { apiFetch, clearTokens } from "@/lib/api";

type Usuario = {
  nombre_usuario: string;
  nombre: string;
  apellido: string;
} | null;

export function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [usuario, setUsuario] = useState<Usuario>(null);
  const [cargado, setCargado] = useState(false);

  useEffect(() => {
    // En la home (landing) no hay navbar ni sesión que consultar.
    if (pathname === "/") return;
    apiFetch<Usuario>("/api/auth/user/")
      .then((u) => setUsuario(u))
      .catch(() => setUsuario(null))
      .finally(() => setCargado(true));
  }, [pathname]);

  // La página principal no lleva navbar.
  if (pathname === "/") return null;

  async function logout() {
    try {
      // dj-rest-auth blacklistea el refresh desde la cookie httpOnly (con
      // `credentials: "include"` la cookie viaja automáticamente).
      await apiFetch("/api/auth/logout/", { method: "POST" });
    } catch {
      // se limpia el estado local aunque el logout remoto falle
    } finally {
      clearTokens();
      router.push("/");
    }
  }

  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <Link href="/" className="text-lg font-bold text-foreground">
          FilmAI
        </Link>

        <div className="flex items-center gap-3">
          {cargado && usuario ? (
            <>
              <span className="text-sm text-muted-foreground">
                Hola, <span className="text-foreground">@{usuario.nombre_usuario}</span>
              </span>
              <Button variant="outline" size="sm" onClick={logout}>
                Cerrar sesión
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={() => router.push("/login")}>
                Iniciar sesión
              </Button>
              <Button size="sm" onClick={() => router.push("/register")}>
                Registrarse
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
