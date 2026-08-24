"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

import { GoogleButton } from "@/components/GoogleButton";
import { Button } from "@/components/ui/button";
import { ApiError, apiFetch, storeTokens } from "@/lib/api";
import { handleGoogleLogin } from "@/lib/google-auth";
import { validarCorreo } from "@/lib/validation";

const inputClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [identificador, setIdentificador] = useState("");
  const [password, setPassword] = useState("");
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Modal de recuperación de contraseña (CU-020).
  const [modalRecuperar, setModalRecuperar] = useState(false);
  const [correoRecuperar, setCorreoRecuperar] = useState("");
  const [errorCorreo, setErrorCorreo] = useState<string | null>(null);
  const [loadingRecuperar, setLoadingRecuperar] = useState(false);

  const destino = (() => {
    const next = searchParams.get("next");
    return next && next.startsWith("/") ? next : "/";
  })();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const esEmail = identificador.includes("@");
      const payload = {
        password,
        ...(esEmail ? { email: identificador } : { username: identificador }),
      };
      const data = await apiFetch<{
        access: string;
        refresh: string;
        user?: { nombre_usuario?: string };
      }>("/api/auth/login/", {
        method: "POST",
        body: payload,
        auth: false,
      });
      storeTokens(data.access, data.refresh);
      toast.success(
        data.user?.nombre_usuario
          ? `¡Hola de nuevo, @${data.user.nombre_usuario}!`
          : "¡Sesión iniciada! Bienvenido a FilmAI."
      );
      // docs/04:635 — éxito de login → redirect al Home (hoy la landing "/";
      // cuando exista el catálogo de A-06 se actualiza el destino).
      router.push(destino);
    } catch {
      // docs/04:634 — el error de login siempre es genérico.
      setError("Email, usuario o contraseña incorrectos.");
    } finally {
      setLoading(false);
    }
  }

  async function onGoogle(idToken: string) {
    setError(null);
    setLoading(true);
    try {
      const result = await handleGoogleLogin(idToken);
      if (result.ok) {
        toast.success(
          result.usuario
            ? `¡Hola de nuevo, @${result.usuario}!`
            : "¡Sesión iniciada! Bienvenido a FilmAI."
        );
        router.push(destino);
      } else if (result.faltaCampos) {
        router.push("/completar-google");
      } else {
        setError(result.error);
      }
    } finally {
      setLoading(false);
    }
  }

  function cerrarModalRecuperar() {
    setModalRecuperar(false);
    setCorreoRecuperar("");
    setErrorCorreo(null);
  }

  // CU-020 paso 6: el mensaje de éxito se muestra siempre, exista o no el
  // correo en la base de datos (por seguridad no se revela).
  async function onSubmitRecuperar(e: FormEvent) {
    e.preventDefault();
    const errorValidacion = validarCorreo(correoRecuperar);
    if (errorValidacion) {
      setErrorCorreo(errorValidacion);
      return;
    }
    setErrorCorreo(null);
    setLoadingRecuperar(true);
    try {
      await apiFetch("/api/auth/password/reset/", {
        method: "POST",
        body: { email: correoRecuperar },
        auth: false,
      });
      toast.success("Te enviamos un email con instrucciones para restablecer tu contraseña.");
      cerrarModalRecuperar();
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setErrorCorreo("Esperá un minuto antes de volver a pedir un enlace.");
      } else {
        setErrorCorreo("No se pudo enviar el email. Intentá de nuevo en unos minutos.");
      }
    } finally {
      setLoadingRecuperar(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8">
        {/* Wireframe docs/04 §5f: el wordmark vive dentro de la caja, sin navbar. */}
        <p className="mb-4 text-center text-2xl font-bold text-foreground">FilmAI</p>
        <h1 className="mb-1 text-2xl font-bold text-foreground">Iniciar sesión</h1>
        <p className="mb-6 text-sm text-muted-foreground">Entrá con tu cuenta de FilmAI.</p>

        <div className="mb-6 flex justify-center">
          <GoogleButton onSuccess={onGoogle} />
        </div>

        <div className="mb-4 flex items-center gap-3 text-xs text-muted-foreground">
          <span className="h-px flex-1 bg-border" />
          o con tu cuenta
          <span className="h-px flex-1 bg-border" />
        </div>

        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">
              Email o nombre de usuario
            </label>
            <input
              className={inputClass}
              value={identificador}
              onChange={(e) => setIdentificador(e.target.value)}
              autoComplete="username"
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Contraseña</label>
            <div className="relative">
              <input
                className={inputClass}
                type={mostrarPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setMostrarPassword((v) => !v)}
                className="absolute inset-y-0 right-3 flex items-center text-muted-foreground"
                aria-label="Mostrar u ocultar contraseña"
              >
                {mostrarPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>

          {/* CU-020: abre el modal de recuperación. */}
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => setModalRecuperar(true)}
              className="text-sm text-primary hover:underline"
            >
              ¿Olvidaste tu contraseña?
            </button>
          </div>

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}

          <Button type="submit" disabled={loading} size="lg">
            {loading ? "Ingresando…" : "Iniciar sesión"}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-muted-foreground">
          ¿No tenés cuenta?{" "}
          <Link href="/register" className="text-primary hover:underline">
            Registrate
          </Link>
        </p>

        {modalRecuperar && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6 backdrop-blur-sm"
            onClick={cerrarModalRecuperar}
            role="presentation"
          >
            <div
              className="w-full max-w-sm rounded-2xl border border-border bg-card p-8"
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-modal="true"
              aria-label="Recuperar contraseña"
            >
              <h2 className="mb-1 text-xl font-bold text-foreground">Recuperar contraseña</h2>
              <p className="mb-6 text-sm text-muted-foreground">
                Ingresá el email asociado a tu cuenta y te enviaremos un enlace para crear una
                contraseña nueva.
              </p>

              <form onSubmit={onSubmitRecuperar} className="flex flex-col gap-4">
                <div>
                  <label
                    htmlFor="correo-recuperar"
                    className="mb-1 block text-sm text-muted-foreground"
                  >
                    Email
                  </label>
                  <input
                    id="correo-recuperar"
                    className={inputClass}
                    type="email"
                    value={correoRecuperar}
                    onChange={(e) => {
                      setCorreoRecuperar(e.target.value);
                      // Si ya había un error (de submit o de red), se limpia
                      // apenas el usuario corrige. No validamos en blur:
                      // la validación de formato corre solo en "Enviar enlace".
                      if (errorCorreo) setErrorCorreo(null);
                    }}
                    autoComplete="email"
                    autoFocus
                  />
                  {errorCorreo && (
                    <p className="mt-1 text-sm text-destructive" role="alert">
                      {errorCorreo}
                    </p>
                  )}
                </div>

                <Button type="submit" disabled={loadingRecuperar} size="lg">
                  {loadingRecuperar ? "Enviando…" : "Enviar enlace"}
                </Button>
                <Button type="button" variant="ghost" onClick={cerrarModalRecuperar}>
                  Cancelar
                </Button>
              </form>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
