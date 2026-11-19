import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch } from "@/lib/api";

/** Lo mínimo que la lista necesita de lo que guarda: el cursor de la página siguiente. */
export type ConCursor = { next: string | null };

/**
 * Lista paginada por cursor: pide la primera página de cada consulta, las
 * siguientes a pedido y deja reintentar. Mientras llega una consulta nueva
 * queda a la vista la anterior, y una respuesta vieja se descarta.
 *
 * - `Pagina`: lo que responde la API. `Datos`: lo que guarda cada pantalla
 *   (ítems, cursor y los totales que use).
 * - `cuenta`: sin valor no se pide nada (la sesión todavía no está); si
 *   cambia, se vuelve a pedir.
 * - `primera`: ruta de la primera página (incluye los filtros: si cambia, se
 *   reinicia la lista). `rutaSiguiente` traduce el cursor `next` a una ruta.
 * - `inicial` y `combinar` arman los datos desde la primera página y al
 *   sumar una siguiente.
 */
export function useCursorList<Pagina extends ConCursor, Datos extends ConCursor>({
  cuenta,
  primera,
  rutaSiguiente,
  inicial,
  combinar,
}: {
  cuenta: string | number | null | undefined;
  primera: string;
  rutaSiguiente: (next: string) => string;
  inicial: (pagina: Pagina) => Datos;
  combinar: (actual: Datos, pagina: Pagina) => Datos;
}) {
  const [datos, setDatos] = useState<Datos | null>(null);
  const [estado, setEstado] = useState<"cargando" | "listo" | "error">("cargando");
  const [mas, setMas] = useState<"quieto" | "cargando" | "error">("quieto");
  const [intento, setIntento] = useState(0);
  // Sube para volver a pedir la primera página sin tocar el resto de la pantalla.
  const [recarga, setRecarga] = useState(0);
  const pedido = useRef(0);
  // Las funciones de la pantalla se leen del último render sin ser dependencias.
  const armar = useRef({ rutaSiguiente, inicial, combinar });
  useEffect(() => {
    armar.current = { rutaSiguiente, inicial, combinar };
  });

  useEffect(() => {
    if (!cuenta) return;
    const id = ++pedido.current;
    setEstado("cargando");
    apiFetch<Pagina>(primera).then(
      (pagina) => {
        if (id !== pedido.current) return;
        setDatos(armar.current.inicial(pagina));
        setEstado("listo");
        setMas("quieto");
      },
      () => {
        if (id === pedido.current) setEstado("error");
      }
    );
  }, [primera, cuenta, intento, recarga]);

  const cargarMas = useCallback(() => {
    if (!datos?.next || mas === "cargando" || estado !== "listo") return;
    const id = pedido.current;
    setMas("cargando");
    apiFetch<Pagina>(armar.current.rutaSiguiente(datos.next)).then(
      (pagina) => {
        if (id !== pedido.current) return;
        setDatos((actual) => (actual ? armar.current.combinar(actual, pagina) : actual));
        setMas("quieto");
      },
      () => {
        if (id === pedido.current) setMas("error");
      }
    );
  }, [datos, mas, estado]);

  return {
    datos,
    setDatos,
    estado,
    mas,
    cargarMas,
    /** Pide de nuevo la siguiente página tras un error. */
    reintentarMas: cargarMas,
    /** Cuenta los reintentos de la primera página (también la usan otras cargas de la pantalla). */
    intento,
    reintentar: () => setIntento((anterior) => anterior + 1),
    /** Vuelve a pedir la primera página (ej. tras agregar un ítem desde afuera). */
    recargarPrimera: () => setRecarga((anterior) => anterior + 1),
    /** Dice si conviene vigilar el centinela. */
    puedeSeguir: Boolean(datos?.next) && mas === "quieto" && estado === "listo",
  };
}
