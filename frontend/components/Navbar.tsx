"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { LogOut, Settings, Star, User } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

const SIN_NAVBAR = ["/", "/login", "/register", "/completar-google"];

const NAV_LINKS = [
  { label: "Inicio", href: "/inicio" },
  { label: "Buscar", href: "/buscar" },
  { label: "Listas", href: "/listas" },
] as const;

type Usuario = {
  nombre_usuario: string;
  nombre: string;
  apellido: string;
} | null;

function iniciales(u: NonNullable<Usuario>): string {
  const iniciales = `${u.nombre.charAt(0)}${u.apellido.charAt(0)}`.toUpperCase();
  if (iniciales.trim()) {
    return iniciales;
  }
  return u.nombre_usuario.charAt(0).toUpperCase() || "?";
}

function noImplementado() {
  toast.info("Todavía no está implementado");
}

export function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [usuario, setUsuario] = useState<Usuario>(null);
  const [cargado, setCargado] = useState(false);
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [confirmarLogout, setConfirmarLogout] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const cancelarRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (SIN_NAVBAR.includes(pathname)) return;
    apiFetch<Usuario>("/api/auth/user/")
      .then((u) => setUsuario(u))
      .catch(() => setUsuario(null))
      .finally(() => setCargado(true));
  }, [pathname]);

  useEffect(() => {
    if (!menuAbierto) return;
    function onClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuAbierto(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuAbierto(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuAbierto]);

  useEffect(() => {
    if (!confirmarLogout) return;
    cancelarRef.current?.focus();
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setConfirmarLogout(false);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [confirmarLogout]);

  if (SIN_NAVBAR.includes(pathname)) return null;

  async function logout() {
    try {
      await apiFetch("/api/auth/logout/", { method: "POST" });
      router.push("/");
    } catch {
      // Mantener la sesión visible y permitir reintentar el logout
    }
  }

  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <div className="flex items-center gap-6">
          <Link href="/inicio" className="text-lg font-bold text-foreground">
            FilmAI
          </Link>
          {cargado && usuario ? (
            <nav aria-label="Principal" className="flex items-center gap-1">
              {NAV_LINKS.map((item) => (
                <button
                  key={item.href}
                  type="button"
                  onClick={noImplementado}
                  className="rounded-lg px-3 py-1.5 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground"
                >
                  {item.label}
                </button>
              ))}
            </nav>
          ) : null}
        </div>

        <div className="flex items-center gap-3">
          {cargado && usuario ? (
            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuAbierto((v) => !v)}
                aria-haspopup="menu"
                aria-expanded={menuAbierto}
                aria-label="Menú de usuario"
                className="flex size-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground"
              >
                {iniciales(usuario)}
              </button>
              {menuAbierto && (
                <div
                  role="menu"
                  aria-label="Opciones de usuario"
                  className="absolute right-0 top-11 z-50 w-48 overflow-hidden rounded-xl border border-border bg-popover shadow-md"
                >
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMenuAbierto(false);
                      noImplementado();
                    }}
                    className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-foreground hover:bg-accent"
                  >
                    <User className="size-4" />
                    Mi perfil
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMenuAbierto(false);
                      noImplementado();
                    }}
                    className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-foreground hover:bg-accent"
                  >
                    <Star className="size-4" />
                    Mis reseñas
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMenuAbierto(false);
                      noImplementado();
                    }}
                    className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-foreground hover:bg-accent"
                  >
                    <Settings className="size-4" />
                    Preferencias
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setMenuAbierto(false);
                      setConfirmarLogout(true);
                    }}
                    className="flex w-full items-center gap-2 border-t border-border px-4 py-2.5 text-left text-sm text-destructive hover:bg-destructive/10"
                  >
                    <LogOut className="size-4" />
                    Cerrar sesión
                  </button>
                </div>
              )}
            </div>
          ) : cargado ? (
            <>
              <Button variant="ghost" size="sm" onClick={() => router.push("/login")}>
                Iniciar sesión
              </Button>
              <Button size="sm" onClick={() => router.push("/register")}>
                Registrarse
              </Button>
            </>
          ) : null}
        </div>
      </div>

      {confirmarLogout && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="titulo-cerrar-sesion"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setConfirmarLogout(false);
          }}
        >
          <div className="w-full max-w-[480px] rounded-xl border border-border bg-card p-6 shadow-lg">
            <h2 id="titulo-cerrar-sesion" className="mb-2 text-lg font-bold text-foreground">
              ¿Está seguro que desea cerrar sesión?
            </h2>
            <p className="mb-6 text-sm text-muted-foreground">
              Tendrás que iniciar sesión nuevamente para volver a acceder a tu cuenta.
            </p>
            <div className="flex justify-end gap-3">
              <Button
                ref={cancelarRef}
                variant="secondary"
                size="sm"
                onClick={() => setConfirmarLogout(false)}
              >
                Cancelar
              </Button>
              <Button variant="destructive" size="sm" onClick={logout}>
                Cerrar sesión
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
