import type { Perfil } from "@/components/AccountProvider";

export type Borrador = Pick<
  Perfil,
  "nombre" | "apellido" | "nombre_usuario" | "pais" | "avatar_id"
>;
export function tieneCambios(borrador: Borrador | null, perfil: Perfil | null) {
  return Boolean(
    borrador &&
    perfil &&
    (Object.keys(borrador) as (keyof Borrador)[]).some((campo) => borrador[campo] !== perfil[campo])
  );
}
