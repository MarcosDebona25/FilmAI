"use client";
import { routes } from "@/lib/routes";

import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
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
  pais: string;
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
  // ¿Ya llegó el perfil? Con él cargado, navegar no lo vuelve a pedir: antes
  // cada cambio de ruta repetía perfil, avatares y preferencias y volvía a
  // renderizar todo lo que usa la cuenta (medición del 22/10/2026).
  const perfilCargado = useRef(false);
  // `recargar` lee la ruta de acá y no de una dependencia: así no cambia en
  // cada navegación, y el valor del contexto tampoco.
  const rutaActual = useRef(pathname);
  useEffect(() => {
    rutaActual.current = pathname;
  }, [pathname]);
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [avatares, setAvatares] = useState<AvatarOption[]>([]);
  const [preferencias, setPreferencias] = useState<Preferencias | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const limpiar = useCallback(() => {
    // Logout, baja o sesión vencida: el backend ya borró las cookies.
    sinCookies.current = true;
    huboSesion.current = false;
    perfilCargado.current = false;
    setPerfil(null);
    setPreferencias(null);
    setAvatares([]);
  }, []);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const nuevoPerfil = await apiFetch<Perfil>("/api/profile/");
      sinCookies.current = false;
      huboSesion.current = true;
      perfilCargado.current = true;
      setPerfil(nuevoPerfil);
      if (nuevoPerfil.idioma && persistLocale(nuevoPerfil.idioma)) router.refresh();
      const [catalogo, ajustes] = await Promise.all([
        apiFetch<AvatarOption[]>("/api/avatars/"),
        apiFetch<Preferencias>("/api/preferences/"),
      ]);
      setAvatares(catalogo);
      setPreferencias(ajustes);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        limpiar();
        const ruta = rutaActual.current;
        if (protectedRoutes.some((protegida) => ruta.startsWith(protegida))) {
          router.replace(`/login?next=${encodeURIComponent(ruta)}`);
        }
      } else {
        // El mensaje del propio error: «Ocurrió un error…» o «No pudimos
        // conectarnos…», en vez del genérico «No pudimos completar la acción».
        setError(err instanceof ApiError ? err.message : translateError({ code: "unknown" }));
      }
    } finally {
      setCargando(false);
    }
  }, [limpiar, router]);

  useEffect(() => {
    if (isAccessPath(pathname)) sinCookies.current = false;
    if (
      ([routes.login, routes.register, routes.completeSignup] as readonly string[]).includes(
        pathname
      ) ||
      sinCookies.current ||
      perfilCargado.current
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

  const actualizarPreferencia = useCallback(
    async function <K extends keyof Preferencias>(campo: K, valor: Preferencias[K]) {
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
      try {
        const confirmada = await apiFetch<Preferencias>("/api/preferences/", {
          method: "PUT",
          body: { [campo]: valor },
        });
        setPreferencias(confirmada);
      } catch (err) {
        setPreferencias(anterior);
        throw err;
      }
    },
    [preferencias, router]
  );

  // El mismo objeto mientras nada cambie: si no, cada render del proveedor
  // (uno por navegación, por `usePathname`) re-renderiza a todos los que usan
  // `useAccount()`.
  const valor = useMemo(
    () => ({
      perfil,
      avatares,
      preferencias,
      cargando,
      error,
      actualizarPerfil: setPerfil,
      actualizarPreferencia,
      recargar,
      limpiar,
    }),
    [perfil, avatares, preferencias, cargando, error, actualizarPreferencia, recargar, limpiar]
  );

  return <AccountContext.Provider value={valor}>{children}</AccountContext.Provider>;
}

export function useAccount() {
  const context = useContext(AccountContext);
  if (!context) throw new Error("useAccount requires AccountProvider");
  return context;
}
