import type { Perfil } from "@/components/AccountProvider";

export type Borrador = Pick<Perfil, "nombre" | "apellido" | "nombre_usuario" | "avatar_id">;
export function tieneCambios(borrador: Borrador | null, perfil: Perfil | null) {
  return Boolean(
    borrador &&
    perfil &&
    (Object.keys(borrador) as (keyof Borrador)[]).some((campo) => borrador[campo] !== perfil[campo])
  );
}

export const ADVERTENCIA_BAJA =
  "Esta acción es irreversible. Se cerrarán todas tus sesiones y no podrás volver a iniciar sesión ni reactivar tu cuenta. Asegurate de querer dar de baja la cuenta antes de continuar.";

export function colorDisponibilidad(estado: string) {
  return estado === "available"
    ? "text-green-700 dark:text-green-400"
    : estado === "taken"
      ? "text-red-700 dark:text-red-400"
      : "text-muted-foreground";
}
