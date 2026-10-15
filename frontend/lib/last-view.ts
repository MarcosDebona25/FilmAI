/**
 * «Última vista» de una pantalla con filtros en la URL: la miga de la ficha
 * vuelve a ella con sus filtros. `sessionStorage` puede no estar (modo
 * privado, datos bloqueados): sin él, la miga lleva a la pantalla sin filtros.
 */
export function crearUltimaVista(clave: string, ruta: string) {
  return {
    guardar(url: string) {
      try {
        window.sessionStorage.setItem(clave, url);
      } catch {
        // Sin almacenamiento no hay vuelta a los filtros; no es un error.
      }
    },
    leer() {
      try {
        const url = window.sessionStorage.getItem(clave);
        // Solo rutas de esta pantalla: lo guardado no puede llevar a otro lado.
        return url?.startsWith(`${ruta}?`) || url === ruta ? url : ruta;
      } catch {
        return ruta;
      }
    },
  };
}
