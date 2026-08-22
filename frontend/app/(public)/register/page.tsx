"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Eye, EyeOff, Info } from "lucide-react";

import { GoogleButton } from "@/components/GoogleButton";
import { Button } from "@/components/ui/button";
import { ApiError, apiFetch } from "@/lib/api";
import { handleGoogleLogin } from "@/lib/google-auth";

const inputClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40";

const GENEROS = [
  { value: "masculino", label: "Masculino" },
  { value: "femenino", label: "Femenino" },
  { value: "no_especifica", label: "No especificar" },
];

/** Fecha máxima para el datepicker: hoy −13 años (enforcement visual; el backend valida). */
function maxFechaNacimiento(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 13);
  return d.toISOString().slice(0, 10);
}

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    nombre: "",
    apellido: "",
    nombre_usuario: "",
    correo: "",
    fecha_nacimiento: "",
    genero: "",
    password1: "",
    password2: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [reenviando, setReenviando] = useState(false);
  const [reenviado, setReenviado] = useState(false);
  const [mostrarPassword1, setMostrarPassword1] = useState(false);
  const [mostrarPassword2, setMostrarPassword2] = useState(false);

  function setField(field: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (form.password1 !== form.password2) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setLoading(true);
    try {
      await apiFetch("/api/auth/registration/", {
        method: "POST",
        body: {
          correo: form.correo,
          nombre_usuario: form.nombre_usuario,
          nombre: form.nombre,
          apellido: form.apellido,
          fecha_nacimiento: form.fecha_nacimiento,
          genero: form.genero,
          password1: form.password1,
          password2: form.password2,
        },
        auth: false,
      });
      setEnviado(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la cuenta.");
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
        router.push("/");
      } else if (result.faltaCampos) {
        router.push("/completar-google");
      } else {
        setError(result.error);
      }
    } finally {
      setLoading(false);
    }
  }

  if (enviado) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center">
          <h1 className="mb-3 text-2xl font-bold text-foreground">Revisá tu bandeja de entrada</h1>
          <p className="mb-6 text-sm text-muted-foreground">
            Te enviamos un enlace de confirmación a{" "}
            <span className="text-foreground">{form.correo}</span>. Si no lo encontrás, revisá la
            carpeta de spam.
          </p>
          <div className="flex flex-col items-center gap-3">
            <button
              type="button"
              disabled={reenviando}
              onClick={async () => {
                setReenviando(true);
                setError(null);
                try {
                  await apiFetch("/api/auth/registration/resend-email/", {
                    method: "POST",
                    body: { email: form.correo },
                    auth: false,
                  });
                  setReenviado(true);
                } catch (err) {
                  setError(err instanceof ApiError ? err.message : "No se pudo reenviar el correo.");
                } finally {
                  setReenviando(false);
                }
              }}
              className="text-sm text-primary hover:underline disabled:opacity-50"
            >
              {reenviando ? "Reenviando…" : reenviado ? "✓ Correo reenviado" : "Reenviar correo"}
            </button>
            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
            <Link href="/login" className="text-primary hover:underline">
              ¿Ya confirmaste? Iniciar sesión
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-8">
        <h1 className="mb-1 text-2xl font-bold text-foreground">Crear cuenta</h1>
        <p className="mb-6 text-sm text-muted-foreground">
          Completá tus datos para registrarte en FilmAI.
        </p>

        <div className="mb-6 flex justify-center">
          <GoogleButton onSuccess={onGoogle} />
        </div>

        <div className="mb-4 flex items-center gap-3 text-xs text-muted-foreground">
          <span className="h-px flex-1 bg-border" />
          o con tu email
          <span className="h-px flex-1 bg-border" />
        </div>

        <form onSubmit={onSubmit} className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Nombre</label>
            <input
              className={inputClass}
              value={form.nombre}
              onChange={(e) => setField("nombre", e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Apellido</label>
            <input
              className={inputClass}
              value={form.apellido}
              onChange={(e) => setField("apellido", e.target.value)}
              required
            />
          </div>
          <div className="col-span-2">
            <label className="mb-1 block text-sm text-muted-foreground">Nombre de usuario</label>
            <input
              className={inputClass}
              value={form.nombre_usuario}
              onChange={(e) => setField("nombre_usuario", e.target.value)}
              placeholder="5-25 caracteres alfanuméricos"
              required
            />
          </div>
          <div className="col-span-2">
            <label className="mb-1 block text-sm text-muted-foreground">Correo</label>
            <input
              className={inputClass}
              type="email"
              value={form.correo}
              onChange={(e) => setField("correo", e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Fecha de nacimiento</label>
            <input
              className={inputClass}
              type="date"
              max={maxFechaNacimiento()}
              value={form.fecha_nacimiento}
              onChange={(e) => setField("fecha_nacimiento", e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Género</label>
            <select
              className={inputClass}
              value={form.genero}
              onChange={(e) => setField("genero", e.target.value)}
              required
            >
              <option value="" disabled>
                Selecciona uno
              </option>
              {GENEROS.map((g) => (
                <option key={g.value} value={g.value}>
                  {g.label}
                </option>
              ))}
            </select>
          </div>
          <div className="col-span-2">
            <label className="mb-1 flex items-center gap-1.5 text-sm text-muted-foreground">
              Contraseña
              <span className="group relative inline-flex">
                <Info className="size-3.5 cursor-help" />
                <span className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 w-56 -translate-x-1/2 rounded-lg border border-border bg-popover p-3 text-left text-xs font-normal text-popover-foreground opacity-0 shadow-md transition-opacity group-hover:opacity-100">
                  La contraseña debe tener:
                  <ul className="mt-1 list-disc space-y-0.5 pl-4">
                    <li>8 a 20 caracteres</li>
                    <li>1 mayúscula</li>
                    <li>1 minúscula</li>
                    <li>1 número</li>
                    <li>1 carácter especial (@#$%&*!)</li>
                  </ul>
                </span>
              </span>
            </label>
            <div className="relative">
              <input
                className={inputClass}
                type={mostrarPassword1 ? "text" : "password"}
                value={form.password1}
                onChange={(e) => setField("password1", e.target.value)}
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                onClick={() => setMostrarPassword1((v) => !v)}
                className="absolute inset-y-0 right-3 flex items-center text-muted-foreground"
                aria-label="Mostrar u ocultar contraseña"
              >
                {mostrarPassword1 ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>
          <div className="col-span-2">
            <label className="mb-1 block text-sm text-muted-foreground">Confirmar contraseña</label>
            <div className="relative">
              <input
                className={inputClass}
                type={mostrarPassword2 ? "text" : "password"}
                value={form.password2}
                onChange={(e) => setField("password2", e.target.value)}
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                onClick={() => setMostrarPassword2((v) => !v)}
                className="absolute inset-y-0 right-3 flex items-center text-muted-foreground"
                aria-label="Mostrar u ocultar contraseña"
              >
                {mostrarPassword2 ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>

          {error && (
            <p className="col-span-2 text-sm text-destructive" role="alert">
              {error}
            </p>
          )}

          <Button type="submit" disabled={loading} size="lg" className="col-span-2">
            {loading ? "Creando cuenta…" : "Crear cuenta"}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-muted-foreground">
          ¿Ya tenés cuenta?{" "}
          <Link href="/login" className="text-primary hover:underline">
            Iniciar sesión
          </Link>
        </p>
      </div>
    </main>
  );
}
