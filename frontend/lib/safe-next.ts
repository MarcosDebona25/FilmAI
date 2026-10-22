/**
 * Destino seguro tras el login (`/login?next=…`).
 *
 * `next` viene de la URL, o sea que lo controla quien arma el enlace. Con
 * `startsWith("/")` no alcanza: `//host` y `/\host` empiezan con barra y el
 * navegador los trata como otro sitio. En vez de listar casos, se resuelve
 * `next` como lo haría el navegador (el parser de URL descarta tabulaciones y
 * saltos de línea y convierte `\` en `/`) y solo se acepta si el resultado sigue
 * en el mismo origen. Se usa un origen ficticio para no depender de `window`
 * (el componente también se renderiza en el servidor).
 */
const ORIGEN = "https://filmai.invalid";

export function destinoSeguro(next: string | null | undefined, porDefecto: string) {
  if (!next || !next.startsWith("/")) return porDefecto;
  let url: URL;
  try {
    url = new URL(next, ORIGEN);
  } catch {
    return porDefecto;
  }
  if (url.origin !== ORIGEN) return porDefecto;
  const destino = `${url.pathname}${url.search}${url.hash}`;
  // `/..//host` se resuelve a la ruta `//host`, que `router.push` volvería a
  // interpretar como otro sitio.
  if (destino.startsWith("//")) return porDefecto;
  return destino;
}
