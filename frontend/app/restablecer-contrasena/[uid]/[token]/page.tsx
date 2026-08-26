"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Eye, EyeOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError, apiFetch, extraerErroresPorCampo } from "@/lib/api";
import { validarConfirmacion, validarPassword } from "@/lib/validation";

const inputClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40";

type Estado = "formulario" | "ok" | "enlace_invalido";

export default function RestablecerContrasenaPage() {
  const params = useParams<{ uid: string; token: string }>();
  const [estado, setEstado] = useState<Estado>("formulario");

  const [password, setPassword] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [mostrarConfirmacion, setMostrarConfirmacion] = useState(false);
  const [errorPassword, setErrorPassword] = useState<string | null>(null);
  const [errorConfirmacion, setErrorConfirmacion] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function validarEnBlur(
    valor: string,
    set: (msg: string | null) => void,
    validador: () => string | null
  ) {
    set(valor ? validador() : null);
  }

  // CU-020: el enlace es válido durante 1 hora. Si el backend responde
  // `codigo: invalido` (token vencido o manipulado), se muestra la pantalla
  // de enlace inválido en lugar del formulario.
  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const errPass = validarPassword(password);
    const errConf = validarConfirmacion(password, confirmacion);
    if (errPass || errConf) {
      setErrorPassword(errPass);
      setErrorConfirmacion(errConf);
      return;
    }
    setErrorPassword(null);
    setErrorConfirmacion(null);
    setLoading(true);
    try {
      await apiFetch("/api/auth/password/reset/confirm/", {
        method: "POST",
        body: {
          uid: params?.uid ? decodeURIComponent(params.uid) : undefined,
          token: params?.token ? decodeURIComponent(params.token) : undefined,
          password1: password,
          password2: confirmacion,
        },
      });
      setEstado("ok");
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        const codigo =
          err.details && typeof err.details === "object"
            ? (err.details as { codigo?: unknown }).codigo
            : undefined;
        if (codigo === "invalido") {
          setEstado("enlace_invalido");
          return;
        }
        const errores = extraerErroresPorCampo(err.details);
        setErrorPassword(errores.password1 ?? errores.new_password1 ?? null);
        setErrorConfirmacion(errores.password2 ?? errores.new_password2 ?? null);
      } else {
        setErrorConfirmacion("No se pudo actualizar la contraseña. Intentá de nuevo.");
      }
    } finally {
      setLoading(false);
    }
  }

  if (estado === "ok") {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center">
          <p className="mb-4 text-2xl font-bold text-foreground">FilmAI</p>
          <h1 className="mb-3 text-2xl font-bold text-foreground">Contraseña actualizada</h1>
          <p className="mb-6 text-sm text-muted-foreground">
            Tu contraseña fue restablecida. Ya podés iniciar sesión con tu nueva contraseña.
          </p>
          <Link href="/login" className="text-primary hover:underline">
            Ir a iniciar sesión
          </Link>
        </div>
      </main>
    );
  }

  if (estado === "enlace_invalido") {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center">
          <p className="mb-4 text-2xl font-bold text-foreground">FilmAI</p>
          <h1 className="mb-3 text-2xl font-bold text-foreground">El enlace no es válido</h1>
          <p className="mb-6 text-sm text-muted-foreground">
            Los enlaces de restablecimiento son válidos durante 1 hora o hasta que se usen. Podés
            pedir uno nuevo desde &quot;¿Olvidaste tu contraseña?&quot; en la pantalla de inicio de
            sesión.
          </p>
          <Link href="/login" className="text-primary hover:underline">
            Volver a iniciar sesión
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8">
        <p className="mb-4 text-center text-2xl font-bold text-foreground">FilmAI</p>
        <h1 className="mb-1 text-2xl font-bold text-foreground">Crear nueva contraseña</h1>
        <p className="mb-6 text-sm text-muted-foreground">
          Elegí una contraseña nueva para tu cuenta.
        </p>

        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div>
            <label htmlFor="nueva-password" className="mb-1 block text-sm text-muted-foreground">
              Nueva contraseña
            </label>
            <div className="relative">
              <input
                id="nueva-password"
                className={inputClass}
                type={mostrarPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onBlur={() =>
                  validarEnBlur(password, setErrorPassword, () => validarPassword(password))
                }
                autoComplete="new-password"
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
            <p className="mt-1 text-xs text-muted-foreground">
              De 8 a 20 caracteres, con mayúscula, minúscula, número y carácter especial
              (@#$%&amp;!).
            </p>
            {errorPassword && (
              <p className="mt-1 text-sm text-destructive" role="alert">
                {errorPassword}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="confirmar-password"
              className="mb-1 block text-sm text-muted-foreground"
            >
              Confirmar contraseña
            </label>
            <div className="relative">
              <input
                id="confirmar-password"
                className={`${inputClass} pr-10`}
                type={mostrarConfirmacion ? "text" : "password"}
                value={confirmacion}
                onChange={(e) => setConfirmacion(e.target.value)}
                onBlur={() =>
                  validarEnBlur(confirmacion, setErrorConfirmacion, () =>
                    validarConfirmacion(password, confirmacion)
                  )
                }
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                onClick={() => setMostrarConfirmacion((v) => !v)}
                className="absolute inset-y-0 right-3 flex items-center text-muted-foreground"
                aria-label="Mostrar u ocultar confirmación"
              >
                {mostrarConfirmacion ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
            {errorConfirmacion && (
              <p className="mt-1 text-sm text-destructive" role="alert">
                {errorConfirmacion}
              </p>
            )}
          </div>

          <Button type="submit" disabled={loading} size="lg">
            {loading ? "Guardando…" : "Actualizar contraseña"}
          </Button>
        </form>
      </div>
    </main>
  );
}
