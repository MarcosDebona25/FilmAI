"use client";

import { cn } from "@/lib/utils";

/**
 * Interruptor del canvas (Settings): pista de 52 × 32 con una perilla. Es un
 * `button` con `role="switch"` y `aria-checked`, así el lector de pantalla
 * anuncia «activado» o «desactivado» con el nombre de `labelledBy`.
 */
export function Switch({
  checked,
  onChange,
  labelledBy,
  disabled = false,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  labelledBy: string;
  disabled?: boolean;
}) {
  // El botón mide 44 px de alto (área táctil, doc 05 Q-04); la pista visible
  // es la de 52 × 32 del canvas. La perilla se mueve con `transform`.
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-labelledby={labelledBy}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className="group flex h-11 w-[52px] shrink-0 cursor-pointer items-center focus-visible:outline-none disabled:cursor-wait disabled:opacity-60"
    >
      <span
        aria-hidden="true"
        className={cn(
          "relative h-8 w-full rounded-full transition-colors duration-150 group-focus-visible:outline-2 group-focus-visible:outline-offset-[3px] group-focus-visible:outline-ring motion-reduce:transition-none",
          checked ? "bg-selected" : "bg-raised-2"
        )}
      >
        <span
          className={cn(
            "absolute top-1 left-1 size-6 rounded-full transition-transform duration-150 motion-reduce:transition-none",
            checked ? "translate-x-5 bg-selected-foreground" : "bg-fg-3"
          )}
        />
      </span>
    </button>
  );
}
