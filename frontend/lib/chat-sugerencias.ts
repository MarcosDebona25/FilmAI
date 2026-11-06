/**
 * Sugerencias de la bienvenida del chat. Hay dos grupos: las personales piden algo
 * que el modelo resuelve con el perfil del usuario (sus mejores calificaciones, sus
 * listas), y las generales no dependen de nadie. Ninguna nombra una producción: un
 * título fijo sería ajeno para quien no lo vio, y el chat promete recomendar según
 * lo que calificaste.
 */
export const SUGERENCIAS_PERSONALES = [
  "similar",
  "fromLists",
  "different",
  "unseenClassic",
] as const;

export const SUGERENCIAS_GENERALES = [
  "short",
  "series",
  "family",
  "comedy",
  "thriller",
  "miniseries",
  "popular",
  "hiddenGem",
  "acclaimed",
  "animated",
] as const;

export type SugerenciaId =
  (typeof SUGERENCIAS_PERSONALES)[number] | (typeof SUGERENCIAS_GENERALES)[number];

/** Lo que se muestra antes del primer sorteo (y en el servidor): fijo, para hidratar igual. */
export const SUGERENCIAS_INICIALES: readonly SugerenciaId[] = ["short", "similar", "series"];

/** Saca `cantidad` elementos distintos de `grupo` sin tocarlo (Fisher-Yates parcial). */
function sortear<T>(grupo: readonly T[], cantidad: number, random: () => number): T[] {
  const copia = [...grupo];
  for (let i = 0; i < cantidad; i++) {
    const j = i + Math.floor(random() * (copia.length - i));
    [copia[i], copia[j]] = [copia[j], copia[i]];
  }
  return copia.slice(0, cantidad);
}

/**
 * Tres sugerencias distintas: una personal, para que se vea que el chat usa tus datos,
 * y dos generales. `random` se inyecta para poder probarlo.
 */
export function elegirSugerencias(random: () => number = Math.random): SugerenciaId[] {
  return [
    ...sortear(SUGERENCIAS_PERSONALES, 1, random),
    ...sortear(SUGERENCIAS_GENERALES, 2, random),
  ];
}
