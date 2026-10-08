"use client";
import { routes } from "@/lib/routes";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { persistLocale } from "@/i18n/client";
import type { AppLocale } from "@/i18n/config";
import { translateError } from "@/lib/errors";
import { protectedRoutes } from "@/lib/routes";
import { ApiError, apiFetch } from "@/lib/api";

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

function aplicarTema(tema: Preferencias["tema"]) {
  document.documentElement.classList.toggle("dark", tema === "oscuro");
  document.documentElement.style.colorScheme = tema === "oscuro" ? "dark" : "light";
}

export function AccountProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [avatares, setAvatares] = useState<AvatarOption[]>([]);
  const [preferencias, setPreferencias] = useState<Preferencias | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const limpiar = useCallback(() => {
    setPerfil(null);
    setPreferencias(null);
    setAvatares([]);
    aplicarTema("oscuro");
  }, []);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const nuevoPerfil = await apiFetch<Perfil>("/api/profile/");
      setPerfil(nuevoPerfil);
      if (nuevoPerfil.idioma && persistLocale(nuevoPerfil.idioma)) router.refresh();
      const [catalogo, ajustes] = await Promise.all([
        apiFetch<AvatarOption[]>("/api/avatars/"),
        apiFetch<Preferencias>("/api/preferences/"),
      ]);
      setAvatares(catalogo);
      setPreferencias(ajustes);
      aplicarTema(ajustes.tema);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        limpiar();
        if (protectedRoutes.some((ruta) => pathname.startsWith(ruta))) {
          router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        }
      } else {
        setError(translateError({ code: "unknown" }));
      }
    } finally {
      setCargando(false);
    }
  }, [limpiar, pathname, router]);

  useEffect(() => {
    if (
      ([routes.login, routes.register, routes.completeSignup] as readonly string[]).includes(
        pathname
      )
    ) {
      setCargando(false);
      return;
    }
    void recargar();
  }, [pathname, recargar]);

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
    if (campo === "tema") aplicarTema(valor as Preferencias["tema"]);
    try {
      const confirmada = await apiFetch<Preferencias>("/api/preferences/", {
        method: "PUT",
        body: { [campo]: valor },
      });
      setPreferencias(confirmada);
      aplicarTema(confirmada.tema);
    } catch (err) {
      setPreferencias(anterior);
      aplicarTema(anterior.tema);
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
