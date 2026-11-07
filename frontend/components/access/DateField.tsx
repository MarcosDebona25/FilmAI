"use client";

import { CalendarDays } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import {
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type ChangeEvent,
  type ClipboardEvent,
  type KeyboardEvent,
} from "react";
import { enUS, es } from "react-day-picker/locale";

import { FieldMessage, fieldClass } from "@/components/access/fields";
import { Calendar } from "@/components/ui/calendar";
import type { AppLocale } from "@/i18n/config";
import { translateError } from "@/lib/errors";
import { formatDateInput, isoDeFecha, maskDateInput, parseDateInput } from "@/lib/format";
import { maxFechaNacimiento } from "@/lib/validation";
import { validationError } from "@/lib/validation-error";
import { cn } from "@/lib/utils";

type Props = {
  /** ISO `YYYY-MM-DD`, o `""` mientras no hay una fecha completa y real. */
  value: string;
  onChange: (iso: string) => void;
  label: string;
  name: string;
  id?: string;
  /** Error del formulario, ya traducido (required, futuro, edad mínima, servidor). */
  error?: string | null;
  help?: string;
  reserveMessage?: boolean;
  required?: boolean;
  autoFocus?: boolean;
};

/** Margen entre el campo y el calendario, y entre el calendario y el borde de la ventana. */
const MARGEN_PX = 8;
/** Calendario: locale de date-fns con los textos de react-day-picker y el primer día de la semana. */
const calendarios = {
  es: { locale: es, weekStartsOn: 1 },
  en: { locale: enUS, weekStartsOn: 0 },
} as const;
/** Mes en que abre el calendario con el campo vacío: un ancla neutra, no «hoy − 13». */
const MES_SIN_VALOR = new Date(2000, 0, 1);
const PRIMER_MES = new Date(1900, 0, 1);

function aFecha(iso: string) {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

/**
 * Campo de fecha de nacimiento (07/11/2026). Reemplaza al `<input type="date">`
 * nativo, cuyo orden de día y mes lo decidía el idioma del navegador y no el
 * de la app. Un solo campo de texto con máscara (`es` DD/MM/AAAA, `en`
 * MM/DD/YYYY) y un calendario en un popover, con el locale de la app.
 *
 * El formulario solo ve el ISO: mientras el texto está incompleto recibe `""`
 * y el campo no muestra error (no se marca «obligatorio» a mitad del tipeo).
 * Una fecha completa que no existe (31/02) muestra su propio error.
 *
 * El popover sigue el patrón de `CountrySelect`: se abre debajo (o arriba si
 * no entra), Escape cierra y devuelve el foco al campo, y un clic afuera o
 * sacar el foco lo cierran sin elegir. El teclado dentro del calendario lo
 * maneja react-day-picker.
 */
export function DateField({
  value,
  onChange,
  label,
  name,
  id,
  error,
  help,
  reserveMessage = false,
  required,
  autoFocus,
}: Props) {
  const t = useTranslations("common.fields");
  const locale = useLocale() as AppLocale;
  const generated = useId();
  const fieldId = id ?? generated;
  const infoId = `${fieldId}-info`;
  const panelId = `${fieldId}-calendario`;

  const [texto, setTexto] = useState(() => formatDateInput(value, locale));
  const [salio, setSalio] = useState(false);
  const [abierto, setAbierto] = useState(false);
  const [haciaArriba, setHaciaArriba] = useState(false);

  const contenedor = useRef<HTMLDivElement>(null);
  const campo = useRef<HTMLInputElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  // Idioma con el que se escribió `texto`, para reordenarlo si cambia.
  const localeTexto = useRef(locale);

  // Si el valor cambia desde afuera (o cambia el idioma), el texto lo sigue.
  // Un texto incompleto (valor `""`) se respeta para no borrar lo tipeado.
  useEffect(() => {
    if (localeTexto.current !== locale) {
      localeTexto.current = locale;
      setTexto(value ? formatDateInput(value, locale) : "");
      return;
    }
    if (value && parseDateInput(texto, locale) !== value) setTexto(formatDateInput(value, locale));
    if (!value && parseDateInput(texto, locale)) setTexto("");
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo reacciona al valor y al idioma.
  }, [value, locale]);

  const completo = /^\d{2}\/\d{2}\/\d{4}$/.test(texto);
  const incompleto = texto !== "" && !completo;
  const codigoLocal =
    completo && !parseDateInput(texto, locale)
      ? "date_inexistent"
      : incompleto && salio
        ? "invalid"
        : null;
  const errorLocal = codigoLocal
    ? translateError(validationError(codigoLocal)!, locale, "fecha_nacimiento")
    : null;
  // A mitad del tipeo no se muestra nada; con texto completo y real, el del formulario.
  const visible = errorLocal ?? (incompleto ? null : error);

  function escribir(nuevo: string) {
    setTexto(nuevo);
    onChange(parseDateInput(nuevo, locale) ?? "");
  }

  function alCambiar(evento: ChangeEvent<HTMLInputElement>) {
    const crudo = evento.target.value;
    // El autocompletado del navegador puede dejar el ISO tal cual.
    if (/^\d{4}-\d{2}-\d{2}$/.test(crudo)) {
      escribir(formatDateInput(crudo, locale) || crudo);
      return;
    }
    setSalio(false);
    // Al tipear (el texto crece) se agrega la barra siguiente; al borrar, no.
    escribir(maskDateInput(crudo, crudo.length > texto.length || crudo.endsWith("/")));
  }

  function alPegar(evento: ClipboardEvent<HTMLInputElement>) {
    const pegado = evento.clipboardData.getData("text").trim();
    if (!pegado) return;
    evento.preventDefault();
    // El texto pegado reemplaza al campo entero: «10/04/1992», «10041992» o «1992-04-10».
    escribir(
      /^\d{4}-\d{2}-\d{2}$/.test(pegado)
        ? formatDateInput(pegado, locale)
        : maskDateInput(pegado, false)
    );
  }

  function cerrar(volverAlCampo: boolean) {
    setAbierto(false);
    if (volverAlCampo) campo.current?.focus();
  }

  function elegir(fecha: Date | undefined) {
    // Un clic sobre el día ya elegido lo «deselecciona»: se conserva el valor.
    if (!fecha) return cerrar(true);
    const iso = isoDeFecha(fecha);
    setTexto(formatDateInput(iso, locale));
    onChange(iso);
    cerrar(true);
  }

  // Antes de pintar: si abajo no entra, la página baja lo que falta; solo se
  // abre hacia arriba cuando la página ya no puede bajar más (como CountrySelect).
  useLayoutEffect(() => {
    if (!abierto || !campo.current || !panel.current) return;
    const rect = campo.current.getBoundingClientRect();
    const alto = panel.current.offsetHeight;
    const abajo = window.innerHeight - rect.bottom - MARGEN_PX * 2;
    const encima = rect.top - MARGEN_PX * 2;
    const falta = alto - abajo;
    const scrollRestante =
      document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
    let arriba = false;
    if (falta > 0 && scrollRestante >= falta) {
      window.scrollBy({ top: falta, behavior: "smooth" });
    } else if (falta > 0) {
      arriba = encima > abajo + scrollRestante;
    }
    setHaciaArriba(arriba);
    // El foco entra al calendario, en el día elegido (o el primero habilitado):
    // desde ahí las flechas, Inicio/Fin y RePág/AvPág los maneja react-day-picker.
    panel.current
      .querySelector<HTMLButtonElement>('button[data-day][tabindex="0"]')
      ?.focus({ preventScroll: true });
  }, [abierto]);

  // Un clic o un toque fuera del componente cierra sin elegir.
  useEffect(() => {
    if (!abierto) return;
    const alTocar = (evento: PointerEvent) => {
      if (!contenedor.current?.contains(evento.target as Node)) cerrar(false);
    };
    document.addEventListener("pointerdown", alTocar);
    return () => document.removeEventListener("pointerdown", alTocar);
  }, [abierto]);

  function teclaEnCampo(evento: KeyboardEvent<HTMLDivElement>) {
    if (!abierto || evento.key !== "Escape") return;
    // Que no cierre también un diálogo que contenga al campo.
    evento.preventDefault();
    evento.stopPropagation();
    cerrar(true);
  }

  const max = aFecha(maxFechaNacimiento());
  const seleccionada = value ? aFecha(value) : undefined;
  const { locale: calendarLocale, weekStartsOn } = calendarios[locale];

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={fieldId} className="text-sm font-semibold">
        {label}
      </label>
      <div
        ref={contenedor}
        className="relative"
        onKeyDown={teclaEnCampo}
        onBlur={(evento) => {
          // El foco salió del campo y del calendario: se cierra sin elegir.
          if (abierto && !contenedor.current?.contains(evento.relatedTarget as Node | null))
            cerrar(false);
        }}
      >
        <input
          ref={campo}
          id={fieldId}
          name={name}
          type="text"
          inputMode="numeric"
          autoComplete="bday"
          maxLength={10}
          placeholder={t("dateInputPlaceholder")}
          required={required}
          autoFocus={autoFocus}
          aria-invalid={visible ? true : undefined}
          aria-describedby={infoId}
          value={texto}
          onChange={alCambiar}
          onPaste={alPegar}
          onBlur={() => setSalio(true)}
          className={cn(fieldClass, "pr-[3.25rem] tabular-nums")}
        />
        <button
          type="button"
          aria-label={t("openCalendar")}
          aria-haspopup="dialog"
          aria-expanded={abierto}
          aria-controls={abierto ? panelId : undefined}
          onClick={() => (abierto ? cerrar(true) : setAbierto(true))}
          className="absolute top-1 right-1 grid size-11 place-items-center rounded-lg text-fg-3 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          <CalendarDays aria-hidden="true" className="size-5" />
        </button>
        {abierto && (
          <div
            ref={panel}
            id={panelId}
            role="dialog"
            aria-label={label}
            className={cn(
              "absolute right-0 z-40 rounded-[0.625rem] bg-raised p-1.5 shadow-[inset_0_0_0_1px_var(--line),0_16px_40px_rgb(0_0_0/0.45)]",
              haciaArriba ? "bottom-full mb-2" : "top-full mt-2"
            )}
          >
            <Calendar
              mode="single"
              autoFocus
              captionLayout="dropdown"
              showOutsideDays={false}
              reverseYears
              locale={calendarLocale}
              weekStartsOn={weekStartsOn}
              startMonth={PRIMER_MES}
              endMonth={max}
              defaultMonth={seleccionada ?? MES_SIN_VALOR}
              disabled={{ after: max }}
              selected={seleccionada}
              onSelect={elegir}
              className="bg-transparent [--cell-size:--spacing(10)]"
            />
          </div>
        )}
      </div>
      <FieldMessage id={infoId} error={visible} help={help} reserve={reserveMessage} />
    </div>
  );
}
