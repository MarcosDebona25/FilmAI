"use client";
import { routes } from "@/lib/routes";
import { useTranslations } from "next-intl";
import enums from "@/i18n/enums.json";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { GoogleButton } from "@/components/GoogleButton";
import { completarRegistroGoogle, tieneGooglePendiente } from "@/lib/google-auth";
import { useValidation } from "@/lib/use-validation";

const inputClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40";

type Campo = "nombre_usuario" | "fecha_nacimiento" | "genero";
type Errores = Partial<Record<Campo, string | null>>;

/** Fecha máxima para el datepicker: hoy −13 años (enforcement visual; el backend valida). */
function maxFechaNacimiento(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 13);
  return d.toISOString().slice(0, 10);
}

function ErrorTexto({ mensaje }: { mensaje?: string | null }) {
  if (!mensaje) return null;
  return (
    <p className="mt-1 text-xs text-destructive" role="alert">
      {mensaje}
    </p>
  );
}

export default function CompletarGooglePage() {
  const labels = useTranslations("enums.gender");
  const errors = useTranslations("errors.codes");
  const GENEROS = enums.genderValues.map((value) => ({
    value,
    label: labels(value as "masculino"),
  }));

  const { validarFechaNacimiento, validarNombreUsuario } = useValidation();

  const router = useRouter();
  const [form, setForm] = useState<Record<Campo, string>>({
    nombre_usuario: "",
    fecha_nacimiento: "",
    genero: "",
  });
  const [errores, setErrores] = useState<Errores>({});
  const [tocados, setTocados] = useState<Partial<Record<Campo, boolean>>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Solo se llega acá tras "Continuar con Google" en login/registro (que marcó
  // el flujo pendiente). Si no hay marca, no es un registro Google válido.
  useEffect(() => {
    if (!tieneGooglePendiente()) {
      router.replace(routes.login);
    }
  }, [router]);

  function setField(campo: Campo, valor: string) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  function validarCampo(campo: Campo, valor: string): string | null {
    if (campo === "nombre_usuario") return validarNombreUsuario(valor);
    if (campo === "fecha_nacimiento") return validarFechaNacimiento(valor);
    return valor ? null : errors("required");
  }

  function onBlurCampo(campo: Campo) {
    setTocados((prev) => ({ ...prev, [campo]: true }));
    setErrores((prev) => ({ ...prev, [campo]: validarCampo(campo, form[campo]) }));
  }

  async function onGoogle(idToken: string) {
    if (loading) return;
    setError(null);

    // Validar ANTES de enviar: si falta algo, no se gasta el id_token fresco
    // (es de un solo uso) y se vuelve a tocar el botón de Google.
    const nuevosErrores: Errores = {
      nombre_usuario: validarNombreUsuario(form.nombre_usuario),
      fecha_nacimiento: validarFechaNacimiento(form.fecha_nacimiento),
      genero: form.genero ? null : errors("required"),
    };
    setErrores(nuevosErrores);
    setTocados({ nombre_usuario: true, fecha_nacimiento: true, genero: true });
    if (Object.values(nuevosErrores).some(Boolean)) {
      setError("Completá los campos y tocá de nuevo el botón de Google.");
      return;
    }

    setLoading(true);
    try {
      const result = await completarRegistroGoogle(idToken, {
        nombre_usuario: form.nombre_usuario,
        fecha_nacimiento: form.fecha_nacimiento,
        genero: form.genero,
      });
      if (result.ok) {
        router.push("/");
      } else if (result.erroresPorCampo && Object.keys(result.erroresPorCampo).length > 0) {
        // Errores de campo del backend (p.ej. username ocupado) → inline.
        setErrores((prev) => ({ ...prev, ...result.erroresPorCampo! }));
        setError("Corregí los campos marcados y tocá de nuevo el botón de Google.");
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
        <h1 className="mb-1 text-2xl font-bold text-foreground">Completá tu cuenta</h1>
        <p className="mb-6 text-sm text-muted-foreground">
          Completá tus datos y confirmá con Google.
        </p>

        <form
          onSubmit={(e: FormEvent) => e.preventDefault()}
          noValidate
          className="flex flex-col gap-4"
        >
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Nombre de usuario</label>
            <input
              className={`${inputClass} ${
                tocados.nombre_usuario && errores.nombre_usuario ? "border-destructive" : ""
              }`}
              value={form.nombre_usuario}
              onChange={(e) => setField("nombre_usuario", e.target.value)}
              onBlur={() => onBlurCampo("nombre_usuario")}
              placeholder="5-25 caracteres alfanuméricos"
              aria-invalid={Boolean(tocados.nombre_usuario && errores.nombre_usuario)}
              required
            />
            <ErrorTexto mensaje={tocados.nombre_usuario ? errores.nombre_usuario : undefined} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Fecha de nacimiento</label>
            <input
              className={`${inputClass} ${
                tocados.fecha_nacimiento && errores.fecha_nacimiento ? "border-destructive" : ""
              }`}
              type="date"
              max={maxFechaNacimiento()}
              value={form.fecha_nacimiento}
              onChange={(e) => setField("fecha_nacimiento", e.target.value)}
              onBlur={() => onBlurCampo("fecha_nacimiento")}
              aria-invalid={Boolean(tocados.fecha_nacimiento && errores.fecha_nacimiento)}
              required
            />
            <p className="mt-1 text-xs text-muted-foreground">Formato: dd/mm/aaaa</p>
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

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}

          <div className="flex flex-col items-center gap-2">
            <GoogleButton text="signup_with" onSuccess={onGoogle} onError={(m) => setError(m)} />
          </div>
        </form>
      </div>
    </main>
  );
}
