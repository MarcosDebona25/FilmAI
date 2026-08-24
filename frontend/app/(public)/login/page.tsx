"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Eye, EyeOff } from "lucide-react";

import { GoogleButton } from "@/components/GoogleButton";
import { Button } from "@/components/ui/button";
import { apiFetch, storeTokens } from "@/lib/api";
import { handleGoogleLogin } from "@/lib/google-auth";

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
      const data = await apiFetch<{ access: string; refresh: string }>("/api/auth/login/", {
        method: "POST",
        body: payload,
        auth: false,
      });
      storeTokens(data.access, data.refresh);
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

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8">
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

          {/* Solo visual: el modal de recuperación se implementa en A-07 (CU-020). */}
          <div className="flex justify-end">
            <button type="button" className="text-sm text-primary hover:underline">
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
      </div>
    </main>
  );
}
