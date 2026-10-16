"use client";
import { routes } from "@/lib/routes";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { persistLocale } from "@/i18n/client";
import type { AppLocale } from "@/i18n/config";
import { translateError } from "@/lib/errors";
import { isAccessPath, protectedRoutes } from "@/lib/routes";
import { ApiError, SESION_VENCIDA, apiFetch } from "@/lib/api";

export type Perfil = {
  pk: number;
  idioma: AppLocale | null;
  nombre: string;
  apellido: string;
  nombre_usuario: string;
  correo: string;
  fecha_nacimiento: string;
  genero: string;
  fecha_registro: string;
  avatar_id: number;
  tiene_contrasena_local: boolean;
};

export type AvatarOption = { id: number; src: string };
export type Preferencias = {
  idioma: AppLocale | null;
  tema: "oscuro" | "claro";
  perfil_publico: boolean;
  notif_recomendaciones: boolean;
  notif_resenas: boolean;
  notif_novedades: boolean;
};

type AccountContextValue = {
  perfil: Perfil | null;
  avatares: AvatarOption[];
  preferencias: Preferencias | null;
  cargando: boolean;
  error: string | null;
  actualizarPerfil: (perfil: Perfil) => void;
  actualizarPreferencia: <K extends keyof Preferencias>(
    campo: K,
    valor: Preferencias[K]
  ) => Promise<void>;
  recargar: () => Promise<void>;
  limpiar: () => void;
};

const AccountContext = createContext<AccountContextValue | null>(null);

/**
 * Solo tema oscuro por ahora (15/10/2026): los tokens propios de la app
 * (superficies, líneas, textos, velos) existen solo para oscuro, y con «claro»
 * la interfaz se rompía. La preferencia `tema` se sigue guardando en la API
 * para cuando exista la paleta clara del canvas; hasta entonces se ignora.
 */
function aplicarTema() {
  document.documentElement.classList.add("dark");
  document.documentElement.style.colorScheme = "dark";
}

export function AccountProvider({
  children,
  sesionPosible = true,
}: {
  children: React.ReactNode;
  /**
   * Lo calcula el layout en el servidor: ¿llegó alguna de las cookies
   * `access` o `refresh`? Sin ninguna no hay sesión posible y no se pide el
   * perfil (ese pedido solo contestaría 401).
   */
  sesionPosible?: boolean;
}) {
  const t = useTranslations("auth.session");
  const pathname = usePathname();
  const router = useRouter();
  // Sin cookies no se pregunta por el perfil. Se vuelve a preguntar después
  // de pasar por una pantalla de acceso (ahí se puede iniciar sesión, y el
  // alta con Google no llama a `recargar()`).
  const sinCookies = useRef(!sesionPosible);
  // ¿Hubo una sesión? Distingue «se te venció» de «nunca entraste».
  const huboSesion = useRef(sesionPosible);
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [avatares, setAvatares] = useState<AvatarOption[]>([]);
  const [preferencias, setPreferencias] = useState<Preferencias | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const limpiar = useCallback(() => {
    // Logout, baja o sesión vencida: el backend ya borró las cookies.
    sinCookies.current = true;
    huboSesion.current = false;
    setPerfil(null);
    setPreferencias(null);
    setAvatares([]);
    aplicarTema();
  }, []);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const nuevoPerfil = await apiFetch<Perfil>("/api/profile/");
      sinCookies.current = false;
      huboSesion.current = true;
      setPerfil(nuevoPerfil);
      if (nuevoPerfil.idioma && persistLocale(nuevoPerfil.idioma)) router.refresh();
      const [catalogo, ajustes] = await Promise.all([
        apiFetch<AvatarOption[]>("/api/avatars/"),
        apiFetch<Preferencias>("/api/preferences/"),
      ]);
      setAvatares(catalogo);
      setPreferencias(ajustes);
      aplicarTema();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        limpiar();
        if (protectedRoutes.some((ruta) => pathname.startsWith(ruta))) {
          router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        }
      } else {
        // El mensaje del propio error: «Ocurrió un error…» o «No pudimos
        // conectarnos…», en vez del genérico «No pudimos completar la acción».
        setError(err instanceof ApiError ? err.message : translateError({ code: "unknown" }));
      }
    } finally {
      setCargando(false);
    }
  }, [limpiar, pathname, router]);

  useEffect(() => {
    if (isAccessPath(pathname)) sinCookies.current = false;
    if (
      ([routes.login, routes.register, routes.completeSignup] as readonly string[]).includes(
        pathname
      ) ||
      sinCookies.current
    ) {
      setCargando(false);
      return;
    }
    void recargar();
  }, [pathname, recargar]);

  // Un 401 que ni renovando se resolvió (`apiFetch`): si había sesión, venció
  // (pasaron los 7 días de la cookie `refresh`, o se cerró en otro lado).
  useEffect(() => {
    function alVencer() {
      if (!huboSesion.current) return;
      toast.info(t("expired"));
      limpiar();
      if (protectedRoutes.some((ruta) => pathname.startsWith(ruta)))
        router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
    window.addEventListener(SESION_VENCIDA, alVencer);
    return () => window.removeEventListener(SESION_VENCIDA, alVencer);
  }, [limpiar, pathname, router, t]);

  async function actualizarPreferencia<K extends keyof Preferencias>(
    campo: K,
    valor: Preferencias[K]
  ) {
    if (!preferencias) return;
    const anterior = preferencias;
    if (campo === "idioma") {
      const confirmada = await apiFetch<Preferencias>("/api/preferences/", {
        method: "PUT",
        body: { idioma: valor },
      });
      setPreferencias(confirmada);
      setPerfil((current) => (current ? { ...current, idioma: confirmada.idioma } : current));
      if (confirmada.idioma) {
        persistLocale(confirmada.idioma);
        router.refresh();
      }
      return;
    }
    const optimista = { ...anterior, [campo]: valor };
    setPreferencias(optimista);
    if (campo === "tema") aplicarTema();
    try {
      const confirmada = await apiFetch<Preferencias>("/api/preferences/", {
        method: "PUT",
        body: { [campo]: valor },
      });
      setPreferencias(confirmada);
      aplicarTema();
    } catch (err) {
      setPreferencias(anterior);
      aplicarTema();
      throw err;
    }
  }

  return (
    <AccountContext.Provider
      value={{
        perfil,
        avatares,
        preferencias,
        cargando,
        error,
        actualizarPerfil: setPerfil,
        actualizarPreferencia,
        recargar,
        limpiar,
      }}
    >
      {children}
    </AccountContext.Provider>
  );
}

export function useAccount() {
  const context = useContext(AccountContext);
  if (!context) throw new Error("useAccount requires AccountProvider");
  return context;
}
