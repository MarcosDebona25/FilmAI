import { describe, expect, it } from "vitest";

import {
  elegirSugerencias,
  SUGERENCIAS_GENERALES,
  SUGERENCIAS_INICIALES,
  SUGERENCIAS_PERSONALES,
} from "@/lib/chat-sugerencias";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";

describe("sugerencias de la bienvenida del chat", () => {
  it("devuelve tres distintas: una personal y dos generales", () => {
    // Un random fijo en el tope de cada rango es el caso más propenso a repetir.
    for (const valor of [0, 0.25, 0.5, 0.999]) {
      const elegidas = elegirSugerencias(() => valor);
      expect(new Set(elegidas).size).toBe(3);
      expect(elegidas.filter((id) => SUGERENCIAS_PERSONALES.some((p) => p === id))).toHaveLength(1);
      expect(elegidas.filter((id) => SUGERENCIAS_GENERALES.some((g) => g === id))).toHaveLength(2);
    }
  });

  it("es determinista con un random inyectado y cambia cuando cambia el random", () => {
    expect(elegirSugerencias(() => 0)).toEqual(["similar", "short", "series"]);
    expect(elegirSugerencias(() => 0)).toEqual(elegirSugerencias(() => 0));
    expect(elegirSugerencias(() => 0.999)).not.toEqual(elegirSugerencias(() => 0));
  });

  it("con el random real todas las sugerencias son alcanzables", () => {
    const vistas = new Set<string>();
    for (let i = 0; i < 2000; i++) elegirSugerencias().forEach((id) => vistas.add(id));
    expect(vistas.size).toBe(SUGERENCIAS_PERSONALES.length + SUGERENCIAS_GENERALES.length);
  });

  it("ninguna nombra una producción y todas tienen texto en español e inglés", () => {
    const todas = [...SUGERENCIAS_PERSONALES, ...SUGERENCIAS_GENERALES, ...SUGERENCIAS_INICIALES];
    for (const id of todas) {
      for (const catalogo of [es, en]) {
        const texto = catalogo.chat.welcome.suggestions[id];
        expect(texto, id).toBeTruthy();
        expect(texto).not.toMatch(/Interstellar/i);
      }
    }
  });
});
