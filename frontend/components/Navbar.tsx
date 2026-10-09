"use client";
import { routes } from "@/lib/routes";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { LogOut, Settings, Star, User } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Avatar } from "@/components/Avatar";
import { useAccount } from "@/components/AccountProvider";
import { apiFetch } from "@/lib/api";
import { mantenerFocoEnDialogo } from "@/lib/dialog-focus";

const SIN_NAVBAR = ["/", routes.login, routes.register, routes.completeSignup];

const NAV_LINKS = [
  { label: "Inicio", href: "/inicio" },
  { label: "Buscar", href: "/buscar" },
  { label: "Listas", href: routes.lists },
] as const;

function noImplementado() {
  toast.info("Todavía no está implementado");
}

export function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const { perfil, avatares, cargando, limpiar } = useAccount();
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [confirmarLogout, setConfirmarLogout] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const firstItemRef = useRef<HTMLAnchorElement>(null);
  const cancelarRef = useRef<HTMLButtonElement>(null);
  const logoutDialogRef = useRef<HTMLDivElement>(null);

  function cerrarLogout() {
    setConfirmarLogout(false);
    menuButtonRef.current?.focus();
  }

  useEffect(() => {
    if (!menuAbierto) return;
    firstItemRef.current?.focus();
    function onClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuAbierto(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setMenuAbierto(false);
        menuButtonRef.current?.focus();
      } else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
        const items = Array.from(
          menuRef.current?.querySelectorAll<HTMLElement>("[role='menuitem']") ?? []
        );
        if (!items.length) return;
        e.preventDefault();
        const actual = items.indexOf(document.activeElement as HTMLElement);
        const siguiente =
          e.key === "Home"
            ? 0
            : e.key === "End"
              ? items.length - 1
              : e.key === "ArrowDown"
                ? (actual + 1) % items.length
                : (actual - 1 + items.length) % items.length;
        items[siguiente].focus();
      }
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
      if (e.key === "Escape") cerrarLogout();
      mantenerFocoEnDialogo(e, logoutDialogRef.current);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [confirmarLogout]);

  if (SIN_NAVBAR.includes(pathname)) return null;

  async function logout() {
    try {
      await apiFetch("/api/auth/logout/", { method: "POST" });
      limpiar();
      setConfirmarLogout(false);
      router.push("/");
    } catch {
      // Mantener la sesión visible y permitir reintentar el logout
    }
  }

  return (
    <header className="border-b border-border bg-card">
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-card focus:p-3 focus:text-foreground focus:outline-2 focus:outline-ring"
      >
        Saltar al contenido
      </a>
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <div className="flex items-center gap-6">
          <Link href="/" className="text-lg font-bold text-foreground">
            FilmAI
          </Link>
          {!cargando && perfil ? (
            <nav aria-label="Principal" className="hidden items-center gap-1 sm:flex">
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
          {!cargando && perfil ? (
            <div className="relative" ref={menuRef}>
              <button
                ref={menuButtonRef}
                type="button"
                onClick={() => setMenuAbierto((v) => !v)}
                aria-haspopup="menu"
                aria-expanded={menuAbierto}
                aria-label="Menú de usuario"
                className="flex size-11 items-center justify-center rounded-full text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                <Avatar perfil={perfil} avatares={avatares} size={40} />
              </button>
              {menuAbierto && (
                <div
                  role="menu"
                  aria-label="Opciones de usuario"
                  className="absolute right-0 top-11 z-50 w-48 overflow-hidden rounded-xl border border-border bg-popover shadow-md"
                >
                  <Link
                    ref={firstItemRef}
                    href={routes.profile}
                    role="menuitem"
                    onClick={() => setMenuAbierto(false)}
                    className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-foreground hover:bg-accent"
                  >
                    <User className="size-4" />
                    Mi perfil
                  </Link>
                  <Link
                    href={routes.myReviews}
                    role="menuitem"
                    onClick={() => setMenuAbierto(false)}
                    className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-foreground hover:bg-accent"
                  >
                    <Star className="size-4" />
                    Mis reseñas
                  </Link>
                  <Link
                    href={routes.settings}
                    role="menuitem"
                    onClick={() => setMenuAbierto(false)}
                    className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-foreground hover:bg-accent"
                  >
                    <Settings className="size-4" />
                    Preferencias
                  </Link>
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
          ) : !cargando ? (
            <>
              <Button variant="ghost" size="sm" onClick={() => router.push(routes.login)}>
                Iniciar sesión
              </Button>
              <Button size="sm" onClick={() => router.push(routes.register)}>
                Registrarse
              </Button>
            </>
          ) : null}
        </div>
      </div>

      {confirmarLogout && (
        <div
          ref={logoutDialogRef}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="titulo-cerrar-sesion"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) cerrarLogout();
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
              <Button ref={cancelarRef} variant="secondary" size="sm" onClick={cerrarLogout}>
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
