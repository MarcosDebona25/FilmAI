"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { apiFetch, clearTokens } from "@/lib/api";

// Rutas sin navbar: landing (docs/04 §5a) y pantallas de autenticación,
// que son pantalla completa con la caja centrada (docs/04 §5f).
const SIN_NAVBAR = ["/", "/login", "/register"];

type Usuario = {
  nombre_usuario: string;
  nombre: string;
  apellido: string;
} | null;

function iniciales(u: NonNullable<Usuario>): string {
  return `${u.nombre.charAt(0)}${u.apellido.charAt(0)}`.toUpperCase();
}

export function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [usuario, setUsuario] = useState<Usuario>(null);
  const [cargado, setCargado] = useState(false);
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [confirmarLogout, setConfirmarLogout] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // En las rutas sin navbar no hay sesión que consultar.
    if (SIN_NAVBAR.includes(pathname)) return;
    apiFetch<Usuario>("/api/auth/user/")
      .then((u) => setUsuario(u))
      .catch(() => setUsuario(null))
      .finally(() => setCargado(true));
  }, [pathname]);

  // El menú se cierra al clickear fuera o presionar Escape (docs/05 P-07).
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

  // La landing y las pantallas de autenticación no llevan navbar.
  if (SIN_NAVBAR.includes(pathname)) return null;

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
                  {/* Alcance actual: solo Cerrar sesión. El dropdown completo
                      (Mi perfil / Mis reseñas / Preferencias) llega con P-02+. */}
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
              <Button variant="secondary" size="sm" onClick={() => setConfirmarLogout(false)}>
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
