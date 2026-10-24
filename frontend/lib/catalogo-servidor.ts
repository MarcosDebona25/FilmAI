/**
 * Pedidos al catálogo desde el servidor de Next (Hero del Inicio, 24/10/2026).
 *
 * El navegador llega a la API por `NEXT_PUBLIC_API_URL` (`localhost:8000`), pero
 * dentro de Docker `localhost` es el propio contenedor del frontend: el servidor
 * llega al backend por su nombre de servicio, en `API_URL_INTERNA`
 * (`http://backend:8000` en `docker-compose.yml`). Sin esa variable no se pide
 * nada y el navegador hace todo como antes; así corre también el CI.
 *
 * Nunca falla: ante un error o una demora devuelve `null` y el navegador pide
 * el dato por su cuenta. La respuesta queda en la caché de datos de Next por
 * 5 minutos, igual que en el navegador, así el Inicio no espera al backend en
 * cada visita.
 */

/**
 * Más que esto y conviene mandar el HTML sin el Hero: lo pide el navegador. Es
 * poco a propósito: el HTML entero espera este pedido. Pasa solo sin copia en la
 * caché de Next (al arrancar el servidor), porque con una copia vencida Next
 * sirve la vieja y la renueva por detrás. Tendencias desde Redis tarda ~50 ms.
 */
const ESPERA_MAXIMA_MS = 500;
/** Igual que `CACHE_NAVEGADOR_SEGUNDOS` del backend. */
const REVALIDAR_SEGUNDOS = 5 * 60;

export async function pedirAlCatalogo<T>(path: string, idioma: string): Promise<T | null> {
  const base = process.env.API_URL_INTERNA?.replace(/\/$/, "");
  if (!base) return null;
  try {
    const respuesta = await fetch(`${base}${path}`, {
      // La API traduce títulos y géneros según este encabezado; también separa
      // la caché de Next por idioma.
      headers: { "Accept-Language": idioma },
      next: { revalidate: REVALIDAR_SEGUNDOS },
      signal: AbortSignal.timeout(ESPERA_MAXIMA_MS),
    });
    if (!respuesta.ok) return null;
    return (await respuesta.json()) as T;
  } catch {
    return null;
  }
}

/** Las respuestas que llegaron, por ruta; las que fallaron no están. */
export async function pedirVarias(
  paths: string[],
  idioma: string
): Promise<Record<string, unknown>> {
  const respuestas = await Promise.all(paths.map((path) => pedirAlCatalogo(path, idioma)));
  return Object.fromEntries(
    paths.flatMap((path, i) => (respuestas[i] === null ? [] : [[path, respuestas[i]]]))
  );
}
