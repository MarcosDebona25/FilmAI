import { readFileSync, readdirSync, statSync } from "node:fs";
import { relative, resolve } from "node:path";

// TMDB pide nombrarlo solo «TMDB» o «The Movie Database», y que los enlaces a su
// sitio apunten a https://www.themoviedb.org (issue #180).
const SITIO = /^https:\/\/www\.themoviedb\.org\/?$/;
const ENLACES = /https?:\/\/[^\s)"'<>\]]*themoviedb[^\s)"'<>\]]*/gi;
const GRAFIAS = [/\bTMDb\b/, /\bTmdb\b/, /\bThe ?Movie ?DB\b/, /\bthemoviedb\b/i];

/** Devuelve cada grafía o enlace incorrecto que aparece en `text`. */
export function wrongTmdbNames(text) {
  const found = [];
  for (const link of text.match(ENLACES) ?? []) if (!SITIO.test(link)) found.push(link);
  const sinEnlaces = text.replace(ENLACES, " ");
  for (const grafia of GRAFIAS) {
    const hit = sinEnlaces.match(grafia);
    if (hit) {
      found.push(hit[0]);
      break; // una grafía por texto alcanza para nombrarlo
    }
  }
  return found;
}

function flatten(object, prefix = "") {
  return Object.entries(object).flatMap(([key, value]) =>
    typeof value === "string" ? [[`${prefix}${key}`, value]] : flatten(value, `${prefix}${key}.`)
  );
}

function files(directory, filter) {
  return readdirSync(directory).flatMap((name) => {
    const path = resolve(directory, name);
    if (statSync(path).isDirectory()) return files(path, filter);
    return filter(path) ? [path] : [];
  });
}

/**
 * Revisa los textos que ve una persona: catálogos de la interfaz, texto legal,
 * plantillas de correo, prompt del chat y los CSV de traducciones.
 * `extra` suma textos sueltos (`origen: texto`) para probar la regla.
 */
export function namingViolations(frontendRoot, { extra = {} } = {}) {
  const repo = resolve(frontendRoot, "..");
  const violations = [];
  const check = (origin, text) => {
    for (const wrong of wrongTmdbNames(text)) violations.push(`${origin}: «${wrong}»`);
  };
  for (const locale of ["en", "es"]) {
    const catalog = JSON.parse(
      readFileSync(resolve(frontendRoot, `messages/${locale}/common.json`))
    );
    for (const [key, value] of flatten(catalog))
      check(`messages/${locale}/common.json#${key}`, value);
  }
  const lineByLine = [
    ...files(resolve(frontendRoot, "content/legal"), (p) => p.endsWith(".md")),
    ...files(resolve(repo, "backend/templates/correos"), () => true),
    ...files(resolve(repo, "traducciones"), (p) => p.endsWith(".csv")),
    resolve(repo, "backend/chatbot/prompts.py"),
  ];
  for (const path of lineByLine)
    readFileSync(path, "utf8")
      .split("\n")
      .forEach((line, index) => check(`${relative(repo, path)}:${index + 1}`, line));
  for (const [origin, text] of Object.entries(extra)) check(origin, text);
  return violations;
}
