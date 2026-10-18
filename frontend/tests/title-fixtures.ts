/** Datos reales de TMDB para las pruebas de la ficha (C-07). */

// Recortes reales de `movie/157336` y `tv/1396` (en-US), verificados el 14/10/2026.
export const INTERSTELLAR = {
  id: 157336,
  title: "Interstellar",
  tagline: "Mankind was born on Earth. It was never meant to die here.",
  overview:
    "The adventures of a group of explorers who make use of a newly discovered wormhole to surpass the limitations on human space travel and conquer the vast distances involved in an interstellar voyage.",
  release_date: "2014-11-04",
  runtime: 169,
  vote_average: 8.49,
  vote_count: 41471,
  genres: [
    { id: 12, name: "Adventure" },
    { id: 18, name: "Drama" },
    { id: 878, name: "Science Fiction" },
  ],
  poster_path: "/yQvGrMoipbRoddT0ZR8tPoR7NfX.jpg",
  backdrop_path: "/8sNiAPPYU14PUepFNeSNGUTiHW.jpg",
};
export const BREAKING_BAD = {
  id: 1396,
  name: "Breaking Bad",
  tagline: "Change the equation.",
  first_air_date: "2008-01-20",
  number_of_seasons: 5,
  number_of_episodes: 62,
  vote_average: 8.955,
  vote_count: 18830,
  genres: [
    { id: 18, name: "Drama" },
    { id: 80, name: "Crime" },
  ],
  poster_path: "/anFx9aTOOYqgS3v7x3R84Kz67ly.jpg",
  backdrop_path: "/tsRy63Mu5cu8etL1X7ZLyf7UP1M.jpg",
};

// Créditos reales (`movie/157336/credits`, `tv/1396/credits` + `created_by`), ya
// en la forma de `GET /api/catalogo/{tipo}/{id}/credits/`.
export const CREDITOS_INTERSTELLAR = {
  directores: ["Christopher Nolan"],
  reparto: [
    { nombre: "Matthew McConaughey", personaje: "Cooper" },
    { nombre: "Anne Hathaway", personaje: "Brand" },
    { nombre: "Michael Caine", personaje: "Professor Brand" },
  ],
};
export const CREDITOS_BREAKING_BAD = {
  directores: ["Vince Gilligan"],
  reparto: [
    { nombre: "Bryan Cranston", personaje: "Walter White" },
    { nombre: "Aaron Paul", personaje: "Jesse Pinkman" },
  ],
};

// Forma de `GET /api/catalogo/{tipo}/{id}/providers/?pais=AR` (logos reales de TMDB).
export const PLATAFORMAS_AR = {
  pais: "AR",
  enlace: "https://www.themoviedb.org/movie/157336-interstellar/watch?locale=AR",
  suscripcion: [
    { id: 8, nombre: "Netflix", logo: "/pbpMk2JmcoNnQwx5JGpXngfoWtp.jpg" },
    { id: 119, nombre: "Amazon Prime Video", logo: "/emthp39XA2YScoYL1p0sdbAH2WA.jpg" },
  ],
  gratis: [],
  alquiler: [{ id: 2, nombre: "Apple TV", logo: "/9ghgSC0MA082EL6HLCW3GalykFD.jpg" }],
  compra: [{ id: 8, nombre: "Netflix", logo: "/pbpMk2JmcoNnQwx5JGpXngfoWtp.jpg" }],
};
export const PLATAFORMAS_CN = {
  pais: "CN",
  enlace: null,
  suscripcion: [],
  gratis: [],
  alquiler: [],
  compra: [],
};
