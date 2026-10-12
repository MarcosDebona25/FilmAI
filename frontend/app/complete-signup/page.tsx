"use client";
import { routes } from "@/lib/routes";
import { useTranslations } from "next-intl";
import enums from "@/i18n/enums.json";

import Link from "next/link";
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
  const auth = useTranslations("auth.signUp");
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
  // «Sucio» = el usuario escribió o eligió algo; foco y blur no muestran errores.
  const [sucios, setSucios] = useState<Partial<Record<Campo, boolean>>>({});
  const [erroresServidor, setErroresServidor] = useState<Errores>({});
  const [diferido, setDiferido] = useState(form);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [acepta, setAcepta] = useState(false);

  // Solo se llega acá tras "Continuar con Google" en login/registro (que marcó
  // el flujo pendiente). Si no hay marca, no es un registro Google válido.
  useEffect(() => {
    if (!tieneGooglePendiente()) {
      router.replace(routes.login);
    }
  }, [router]);

  useEffect(() => {
    const id = setTimeout(() => setDiferido(form), 600);
    return () => clearTimeout(id);
  }, [form]);

  function setField(campo: Campo, valor: string) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
    setSucios((prev) => ({ ...prev, [campo]: true }));
    setErroresServidor((prev) => ({ ...prev, [campo]: undefined }));
  }

  function validarCampo(campo: Campo, valor: string): string | null {
    if (campo === "nombre_usuario") return validarNombreUsuario(valor);
    if (campo === "fecha_nacimiento") return validarFechaNacimiento(valor);
    return valor ? null : errors("required");
  }

  /** Error visible: solo si ya lo modificó; el texto espera a una pausa. */
  function mostrar(campo: Campo): string | undefined {
    if (erroresServidor[campo]) return erroresServidor[campo] ?? undefined;
    if (!sucios[campo]) return undefined;
    const actual = validarCampo(campo, form[campo]);
    if (!actual) return undefined;
    if (campo !== "nombre_usuario") return actual;
    return validarCampo(campo, diferido[campo]) ? actual : undefined;
  }

  const formularioValido =
    acepta && (Object.keys(form) as Campo[]).every((campo) => !validarCampo(campo, form[campo]));

  async function onGoogle(idToken: string) {
    if (loading) return;
    setError(null);

    // El botón de Google solo está activo con el formulario válido; esto es un
    // resguardo para no gastar el id_token (de un solo uso) con datos inválidos.
    if (!formularioValido) return;

    setLoading(true);
    try {
      const result = await completarRegistroGoogle(idToken, {
        nombre_usuario: form.nombre_usuario,
        fecha_nacimiento: form.fecha_nacimiento,
        genero: form.genero,
        acepta_terminos: true,
      });
      if (result.ok) {
        router.push("/");
      } else if (result.erroresPorCampo && Object.keys(result.erroresPorCampo).length > 0) {
        // Errores de campo del backend (p.ej. username ocupado) → inline.
        setErroresServidor((prev) => ({ ...prev, ...result.erroresPorCampo! }));
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
              className={`${inputClass} ${mostrar("nombre_usuario") ? "border-destructive" : ""}`}
              value={form.nombre_usuario}
              onChange={(e) => setField("nombre_usuario", e.target.value)}
              placeholder="5-25 caracteres alfanuméricos"
              aria-invalid={Boolean(mostrar("nombre_usuario"))}
              required
            />
            <ErrorTexto mensaje={mostrar("nombre_usuario")} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Fecha de nacimiento</label>
            <input
              className={`${inputClass} ${mostrar("fecha_nacimiento") ? "border-destructive" : ""}`}
              type="date"
              max={maxFechaNacimiento()}
              value={form.fecha_nacimiento}
              onChange={(e) => setField("fecha_nacimiento", e.target.value)}
              aria-invalid={Boolean(mostrar("fecha_nacimiento"))}
              required
            />
            <p className="mt-1 text-xs text-muted-foreground">Formato: dd/mm/aaaa</p>
            <ErrorTexto mensaje={mostrar("fecha_nacimiento")} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Género</label>
            <select
              className={`${inputClass} ${mostrar("genero") ? "border-destructive" : ""}`}
              value={form.genero}
              onChange={(e) => setField("genero", e.target.value)}
              aria-invalid={Boolean(mostrar("genero"))}
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
            <ErrorTexto mensaje={mostrar("genero")} />
          </div>

          <div className="flex flex-col gap-1">
            <div className="flex items-start gap-3">
              <input
                id="terminos"
                type="checkbox"
                checked={acepta}
                onChange={(e) => {
                  setAcepta(e.target.checked);
                }}
                className="mt-0.5 size-5 flex-none accent-primary"
              />
              <label htmlFor="terminos" className="text-sm text-muted-foreground">
                {auth.rich("termsAcceptance", {
                  terms: (chunks) => (
                    <Link
                      href={routes.terms}
                      target="_blank"
                      rel="noopener"
                      className="font-semibold text-foreground underline"
                    >
                      {chunks}
                      <span className="sr-only"> {auth("termsNewTabHint")}</span>
                    </Link>
                  ),
                })}
              </label>
            </div>
          </div>

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}

          <div className="flex flex-col items-center gap-2">
            {/* `inert`: sin el formulario válido el botón de Google no se puede usar. */}
            <div inert={!formularioValido} className={formularioValido ? "" : "opacity-50"}>
              <GoogleButton text="signup_with" onSuccess={onGoogle} onError={(m) => setError(m)} />
            </div>
            {!formularioValido && (
              <p className="text-center text-[13px] text-muted-foreground">
                {auth("submitPending")}
              </p>
            )}
          </div>
        </form>
      </div>
    </main>
  );
}
