"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api";

export type Perfil = {
  pk: number;
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
        if (
          ["/perfil", "/preferencias", "/mis-resenas"].some((ruta) => pathname.startsWith(ruta))
        ) {
          router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        }
      } else {
        setError("No pudimos cargar tu cuenta. Intentá de nuevo.");
      }
    } finally {
      setCargando(false);
    }
  }, [limpiar, pathname, router]);

  useEffect(() => {
    if (["/login", "/register", "/completar-google"].includes(pathname)) {
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
  if (!context) throw new Error("useAccount requiere AccountProvider");
  return context;
}
