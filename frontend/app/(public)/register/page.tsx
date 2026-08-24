"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Check, Eye, EyeOff, Info, Loader2, X } from "lucide-react";

import { GoogleButton } from "@/components/GoogleButton";
import { Button } from "@/components/ui/button";
import { ApiError, apiFetch, apiUrl, extraerErroresPorCampo } from "@/lib/api";
import { handleGoogleLogin } from "@/lib/google-auth";
import {
  validarApellido,
  validarConfirmacion,
  validarCorreo,
  validarFechaNacimiento,
  validarNombre,
  validarNombreUsuario,
  validarPassword,
} from "@/lib/validation";

const inputClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40";

const GENEROS = [
  { value: "masculino", label: "Masculino" },
  { value: "femenino", label: "Femenino" },
  { value: "no_especifica", label: "No especificar" },
];

type Campo =
  | "nombre"
  | "apellido"
  | "nombre_usuario"
  | "correo"
  | "fecha_nacimiento"
  | "genero"
  | "password1"
  | "password2";

type Errores = Partial<Record<Campo, string>>;

const VALIDADORES: Record<Campo, (valor: string, form: Record<Campo, string>) => string | null> = {
  nombre: (v) => validarNombre(v),
  apellido: (v) => validarApellido(v),
  nombre_usuario: (v) => validarNombreUsuario(v),
  correo: (v) => validarCorreo(v),
  fecha_nacimiento: (v) => validarFechaNacimiento(v),
  genero: (v) => (v ? null : "Campo obligatorio."),
  password1: (v) => validarPassword(v),
  password2: (v, form) => validarConfirmacion(form.password1, v),
};

/** Fecha máxima para el datepicker: hoy −13 años (enforcement visual; el backend valida). */
function maxFechaNacimiento(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 13);
  return d.toISOString().slice(0, 10);
}

function ErrorTexto({ mensaje }: { mensaje?: string }) {
  if (!mensaje) return null;
  return (
    <p className="mt-1 text-xs text-destructive" role="alert">
      {mensaje}
    </p>
  );
}

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState<Record<Campo, string>>({
    nombre: "",
    apellido: "",
    nombre_usuario: "",
    correo: "",
    fecha_nacimiento: "",
    genero: "",
    password1: "",
    password2: "",
  });
  const [errores, setErrores] = useState<Errores>({});
  const [tocados, setTocados] = useState<Partial<Record<Campo, boolean>>>({});
  const [usernameEstado, setUsernameEstado] = useState<
    "idle" | "checking" | "disponible" | "ocupado"
  >("idle");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [reenviando, setReenviando] = useState(false);
  const [reenviado, setReenviado] = useState(false);
  const [mostrarPassword1, setMostrarPassword1] = useState(false);
  const [mostrarPassword2, setMostrarPassword2] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  function setField(field: Campo, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function validarCampo(campo: Campo, valor: string): string | null {
    return VALIDADORES[campo](valor, form);
  }

  function onBlurCampo(campo: Campo) {
    setTocados((prev) => ({ ...prev, [campo]: true }));
    setErrores((prev) => ({ ...prev, [campo]: validarCampo(campo, form[campo]) }));
  }

  // Disponibilidad de nombre de usuario en tiempo real (A-05), con debounce.
  useEffect(() => {
    const valor = form.nombre_usuario.trim();
    clearTimeout(debounceRef.current);
    if (!valor || validarNombreUsuario(valor)) {
      setUsernameEstado("idle");
      return;
    }
    setUsernameEstado("checking");
    const controller = new AbortController();
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(
          apiUrl(`/api/auth/username-available/?username=${encodeURIComponent(valor)}`),
          { signal: controller.signal }
        );
        const data: { disponible?: boolean } = await res.json();
        setUsernameEstado(data.disponible ? "disponible" : "ocupado");
      } catch {
        if (!controller.signal.aborted) setUsernameEstado("idle");
      }
    }, 400);
    return () => {
      clearTimeout(debounceRef.current);
      controller.abort();
    };
  }, [form.nombre_usuario]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const nuevosErrores: Errores = {};
    for (const campo of Object.keys(VALIDADORES) as Campo[]) {
      const mensaje = VALIDADORES[campo](form[campo], form);
      if (mensaje) nuevosErrores[campo] = mensaje;
    }
    if (Object.keys(nuevosErrores).length > 0) {
      setErrores(nuevosErrores);
      setTocados(Object.fromEntries(Object.keys(nuevosErrores).map((c) => [c, true])));
      return;
    }

    setLoading(true);
    try {
      await apiFetch("/api/auth/registration/", {
        method: "POST",
        body: {
          correo: form.correo,
          nombre_usuario: form.nombre_usuario,
          nombre: form.nombre.trim(),
          apellido: form.apellido.trim(),
          fecha_nacimiento: form.fecha_nacimiento,
          genero: form.genero,
          password1: form.password1,
          password2: form.password2,
        },
        auth: false,
      });
      setEnviado(true);
    } catch (err) {
      if (err instanceof ApiError) {
        // Errores de campo del backend → inline bajo cada input.
        const porCampo = extraerErroresPorCampo(err.details);
        const mapeados: Errores = {};
        for (const campo of Object.keys(VALIDADORES) as Campo[]) {
          if (porCampo[campo]) mapeados[campo] = porCampo[campo];
        }
        if (Object.keys(mapeados).length > 0) {
          setErrores((prev) => ({ ...prev, ...mapeados }));
          setTocados((prev) => ({
            ...prev,
            ...Object.fromEntries(Object.keys(mapeados).map((c) => [c, true])),
          }));
          if ("nombre_usuario" in mapeados) setUsernameEstado("ocupado");
        } else {
          setError(err.message);
        }
      } else {
        setError("No se pudo crear la cuenta.");
      }
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

  const usernameValido = !validarNombreUsuario(form.nombre_usuario);

  function hintUsername() {
    if (usernameEstado === "checking") {
      return (
        <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
          <Loader2 className="size-3 animate-spin" /> Verificando disponibilidad…
        </p>
      );
    }
    if (usernameEstado === "disponible") {
      return (
        <p className="mt-1 flex items-center gap-1 text-xs text-green-600">
          <Check className="size-3" /> Nombre de usuario disponible
        </p>
      );
    }
    if (usernameEstado === "ocupado") {
      return (
        <p className="mt-1 flex items-center gap-1 text-xs text-destructive">
          <X className="size-3" /> Este nombre de usuario no está disponible
        </p>
      );
    }
    return null;
  }

  if (enviado) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center">
          <h1 className="mb-3 text-2xl font-bold text-foreground">Revisá tu bandeja de entrada</h1>
          <p className="mb-6 text-sm text-muted-foreground">
            Te enviamos un enlace de confirmación a{" "}
            <span className="text-foreground">{form.correo}</span>. El enlace es válido durante 24
            horas. Si no lo encontrás, revisá la carpeta de spam.
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
                  setError(
                    err instanceof ApiError ? err.message : "No se pudo reenviar el correo."
                  );
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
        {/* Wireframe docs/04 §5f: el wordmark vive dentro de la caja, sin navbar. */}
        <p className="mb-4 text-center text-2xl font-bold text-foreground">FilmAI</p>
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

        <form onSubmit={onSubmit} noValidate className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Nombre</label>
            <input
              className={`${inputClass} ${tocados.nombre && errores.nombre ? "border-destructive" : ""}`}
              value={form.nombre}
              onChange={(e) => setField("nombre", e.target.value)}
              onBlur={() => onBlurCampo("nombre")}
              aria-invalid={Boolean(tocados.nombre && errores.nombre)}
              required
            />
            <ErrorTexto mensaje={tocados.nombre ? errores.nombre : undefined} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Apellido</label>
            <input
              className={`${inputClass} ${tocados.apellido && errores.apellido ? "border-destructive" : ""}`}
              value={form.apellido}
              onChange={(e) => setField("apellido", e.target.value)}
              onBlur={() => onBlurCampo("apellido")}
              aria-invalid={Boolean(tocados.apellido && errores.apellido)}
              required
            />
            <ErrorTexto mensaje={tocados.apellido ? errores.apellido : undefined} />
          </div>
          <div className="col-span-2">
            <label className="mb-1 block text-sm text-muted-foreground">Nombre de usuario</label>
            <input
              className={`${inputClass} ${
                tocados.nombre_usuario && errores.nombre_usuario
                  ? "border-destructive"
                  : usernameEstado === "disponible"
                    ? "border-green-600"
                    : ""
              }`}
              value={form.nombre_usuario}
              onChange={(e) => setField("nombre_usuario", e.target.value)}
              onBlur={() => onBlurCampo("nombre_usuario")}
              placeholder="5-25 caracteres alfanuméricos"
              aria-invalid={Boolean(tocados.nombre_usuario && errores.nombre_usuario)}
              required
            />
            <ErrorTexto mensaje={tocados.nombre_usuario ? errores.nombre_usuario : undefined} />
            {usernameValido && hintUsername()}
          </div>
          <div className="col-span-2">
            <label className="mb-1 block text-sm text-muted-foreground">Correo</label>
            <input
              className={`${inputClass} ${tocados.correo && errores.correo ? "border-destructive" : ""}`}
              type="email"
              value={form.correo}
              onChange={(e) => setField("correo", e.target.value)}
              onBlur={() => onBlurCampo("correo")}
              aria-invalid={Boolean(tocados.correo && errores.correo)}
              required
            />
            <ErrorTexto mensaje={tocados.correo ? errores.correo : undefined} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Fecha de nacimiento</label>
            <input
              className={`${inputClass} ${tocados.fecha_nacimiento && errores.fecha_nacimiento ? "border-destructive" : ""}`}
              type="date"
              max={maxFechaNacimiento()}
              value={form.fecha_nacimiento}
              onChange={(e) => setField("fecha_nacimiento", e.target.value)}
              onBlur={() => onBlurCampo("fecha_nacimiento")}
              aria-invalid={Boolean(tocados.fecha_nacimiento && errores.fecha_nacimiento)}
              required
            />
            <ErrorTexto mensaje={tocados.fecha_nacimiento ? errores.fecha_nacimiento : undefined} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Género</label>
            <select
              className={`${inputClass} ${tocados.genero && errores.genero ? "border-destructive" : ""}`}
              value={form.genero}
              onChange={(e) => setField("genero", e.target.value)}
              onBlur={() => onBlurCampo("genero")}
              aria-invalid={Boolean(tocados.genero && errores.genero)}
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
            <ErrorTexto mensaje={tocados.genero ? errores.genero : undefined} />
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
                className={`${inputClass} pr-10 ${tocados.password1 && errores.password1 ? "border-destructive" : ""}`}
                type={mostrarPassword1 ? "text" : "password"}
                value={form.password1}
                onChange={(e) => setField("password1", e.target.value)}
                onBlur={() => onBlurCampo("password1")}
                autoComplete="new-password"
                aria-invalid={Boolean(tocados.password1 && errores.password1)}
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
            <ErrorTexto mensaje={tocados.password1 ? errores.password1 : undefined} />
          </div>
          <div className="col-span-2">
            <label className="mb-1 block text-sm text-muted-foreground">Confirmar contraseña</label>
            <div className="relative">
              <input
                className={`${inputClass} pr-10 ${tocados.password2 && errores.password2 ? "border-destructive" : ""}`}
                type={mostrarPassword2 ? "text" : "password"}
                value={form.password2}
                onChange={(e) => setField("password2", e.target.value)}
                onBlur={() => onBlurCampo("password2")}
                autoComplete="new-password"
                aria-invalid={Boolean(tocados.password2 && errores.password2)}
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
            <ErrorTexto mensaje={tocados.password2 ? errores.password2 : undefined} />
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
