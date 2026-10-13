import type { TmdbItem } from "@/lib/catalog";

/**
 * Recortes de respuestas reales de TMDB del 13/10/2026 (los mismos del backend,
 * `catalogo/tests_recomendado.py`). No se inventan datos de TMDB: en C-04a un
 * dato fabricado mantuvo tests en verde mientras producción fallaba.
 */
export const insidious: TmdbItem = {
  id: 1291595,
  media_type: "movie",
  title: "Insidious: Out of the Further",
  overview:
    "Gemma, a young mother raising her daughter in the house she grew up in, discovers she can travel into The Further.",
  poster_path: "/4tTrW9dXCByS5wt2pXVWb58zNjz.jpg",
  backdrop_path: "/p40lmrdI4blcAPZQMTPaiy5v5Ym.jpg",
  release_date: "2026-08-19",
  vote_average: 7.725,
  genre_ids: [27, 53],
};

export const reacher: TmdbItem = {
  id: 108978,
  media_type: "tv",
  name: "Reacher",
  overview:
    "Jack Reacher, a veteran military police investigator, has just recently entered civilian life.",
  poster_path: "/f1VCQIG2iCyOookdgOzwtUpwWC0.jpg",
  backdrop_path: "/pF0qkRsrHkdYadPWY9AMeFZfcwk.jpg",
  first_air_date: "2022-02-03",
  vote_average: 8.136,
  genre_ids: [10759, 80],
};

/** Forma real de `trending/person`: TMDB puede mezclar personas en `trending/all`. */
export const persona: TmdbItem = {
  id: 1,
  media_type: "person",
  name: "Persona de prueba",
  profile_path: "/perfil.jpg",
};
