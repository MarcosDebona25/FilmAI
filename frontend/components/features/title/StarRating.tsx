"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import { useTranslations } from "next-intl";

const NOTAS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
const ESTRELLA =
  "12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2";

/**
 * Diez estrellas como un `radiogroup` (patrón de WAI-ARIA): el mouse
 * previsualiza, el clic elige y el teclado se mueve con flechas, Home y End.
 * Solo la elegida entra en el orden de Tab. Al previsualizar una nota menor,
 * las de la elegida que quedan afuera se ven tenues (canvas). En celular van
 * en dos filas de cinco para mantener objetivos de 44 px.
 */
export function StarRating({
  value,
  onChange,
  onPreview,
  label,
  labelledBy,
  disabled = false,
}: {
  value: number;
  onChange: (nota: number) => void;
  onPreview?: (nota: number) => void;
  label?: string;
  labelledBy?: string;
  disabled?: boolean;
}) {
  const t = useTranslations("common.rating");
  const [hover, setHover] = useState(0);
  const botones = useRef<(HTMLButtonElement | null)[]>([]);
  const vista = hover || value;

  function previsualizar(nota: number) {
    setHover(nota);
    onPreview?.(nota);
  }

  function teclado(event: KeyboardEvent<HTMLButtonElement>) {
    const actual = value || 1;
    const nueva = {
      ArrowRight: Math.min(10, (value || 0) + 1),
      ArrowUp: Math.min(10, (value || 0) + 1),
      ArrowLeft: Math.max(1, actual - 1),
      ArrowDown: Math.max(1, actual - 1),
      Home: 1,
      End: 10,
    }[event.key];
    if (nueva === undefined) return;
    event.preventDefault();
    onChange(nueva);
    botones.current[nueva - 1]?.focus();
  }

  return (
    <div
      role="radiogroup"
      aria-label={label}
      aria-labelledby={labelledBy}
      onMouseLeave={() => previsualizar(0)}
      className="-ml-1.5 grid w-fit grid-cols-5 md:flex"
    >
      {NOTAS.map((nota) => {
        const estado = nota <= vista ? "llena" : hover > 0 && nota <= value ? "tenue" : "vacia";
        return (
          <button
            key={nota}
            ref={(boton) => {
              botones.current[nota - 1] = boton;
            }}
            type="button"
            role="radio"
            aria-checked={nota === value}
            aria-label={t("starValueLabel", { rating: String(nota) })}
            tabIndex={nota === (value || 1) ? 0 : -1}
            disabled={disabled}
            data-estado={estado}
            onClick={() => onChange(nota)}
            onMouseEnter={() => previsualizar(nota)}
            onKeyDown={teclado}
            className="grid size-11 cursor-pointer place-items-center rounded-lg focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-not-allowed"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" className="size-9">
              <polygon
                points={ESTRELLA}
                strokeWidth={estado === "vacia" ? 1.5 : 0}
                strokeLinejoin="round"
                className={
                  estado === "llena"
                    ? "fill-primary"
                    : estado === "tenue"
                      ? "fill-primary opacity-30"
                      : "fill-none stroke-fg-3"
                }
              />
            </svg>
          </button>
        );
      })}
    </div>
  );
}
