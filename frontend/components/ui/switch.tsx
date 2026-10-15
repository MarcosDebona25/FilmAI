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
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-labelledby={labelledBy}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative h-8 w-[52px] shrink-0 cursor-pointer rounded-full transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-[3px] focus-visible:outline-ring disabled:cursor-wait disabled:opacity-60 motion-reduce:transition-none",
        checked ? "bg-selected" : "bg-raised-2"
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "absolute top-1 size-6 rounded-full transition-[left] duration-150 motion-reduce:transition-none",
          checked ? "left-6 bg-selected-foreground" : "left-1 bg-fg-3"
        )}
      />
    </button>
  );
}
