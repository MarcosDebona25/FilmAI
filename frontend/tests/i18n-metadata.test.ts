import { createTranslator } from "next-intl";
import { describe, expect, it, vi } from "vitest";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";

const state = vi.hoisted(() => ({ locale: "es" as "en" | "es" }));
vi.mock("@/app/globals.css", () => ({}));
vi.mock("next/font/google", () => ({
  Hanken_Grotesk: () => ({ variable: "--font-hanken" }),
  Big_Shoulders: () => ({ variable: "--font-big-shoulders" }),
}));
vi.mock("next-intl/server", () => ({
  getLocale: async () => state.locale,
  getTranslations: async (namespace: "legacy.metadata") =>
    createTranslator({
      locale: state.locale,
      messages: state.locale === "es" ? es : en,
      namespace,
    }),
}));

describe("metadatos en los cuatro puntos actuales", () => {
  it.each(["es", "en"] as const)("resuelve títulos y descripción en %s", async (locale) => {
    state.locale = locale;
    const messages = (locale === "es" ? es : en).legacy.metadata;
    const [root, profile, settings, reviews] = await Promise.all([
      import("@/app/layout"),
      import("@/app/profile/layout"),
      import("@/app/settings/layout"),
      import("@/app/my-reviews/page"),
    ]);
    expect(await root.generateMetadata()).toEqual({
      title: "FilmAI",
      description: messages.description,
      icons: { icon: "/icons8-movies-32.png" },
    });
    expect(await profile.generateMetadata()).toEqual({ title: `${messages.profile} | FilmAI` });
    expect(await settings.generateMetadata()).toEqual({ title: `${messages.settings} | FilmAI` });
    // Como el título de la página (canvas): «Calificaciones y reseñas».
    const nav = (locale === "es" ? es : en).nav.main;
    expect(await reviews.generateMetadata()).toEqual({
      title: `${nav.ratingsReviews} | FilmAI`,
    });
  });
});
