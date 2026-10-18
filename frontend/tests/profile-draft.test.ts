import { describe, expect, it } from "vitest";

import type { Perfil } from "@/components/AccountProvider";
import { tieneCambios, type Borrador } from "@/lib/profile-draft";

const perfil = {
  nombre: "Juan",
  apellido: "Pérez",
  nombre_usuario: "juanperez",
  pais: "AR",
  avatar_id: 1,
} as Perfil;
const borrador: Borrador = {
  nombre: "Juan",
  apellido: "Pérez",
  nombre_usuario: "juanperez",
  pais: "AR",
  avatar_id: 1,
};

describe("tieneCambios", () => {
  it("un borrador igual al perfil no tiene cambios", () => {
    expect(tieneCambios(borrador, perfil)).toBe(false);
  });
  it("cambiar el país es un cambio", () => {
    expect(tieneCambios({ ...borrador, pais: "BR" }, perfil)).toBe(true);
  });
  it("sin borrador o sin perfil no hay cambios", () => {
    expect(tieneCambios(null, perfil)).toBe(false);
    expect(tieneCambios(borrador, null)).toBe(false);
  });
});
