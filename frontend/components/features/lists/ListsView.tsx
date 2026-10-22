"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { useAccount } from "@/components/AccountProvider";
import { ListsGridSkeleton } from "@/components/features/lists/ListsGridSkeleton";
import type { AccionLista } from "@/components/features/lists/ListActionsMenu";
import { ListNameDialog } from "@/components/features/lists/ListNameDialog";
import { ConfirmDialog } from "@/components/features/title/ConfirmDialog";
import { mensajeDeError } from "@/components/features/title/RatingDialog";
import { ErrorRetry } from "@/components/ui/ErrorRetry";
import { apiFetch } from "@/lib/api";
import {
  aplicarOrden,
  esPredeterminada,
  personalizadas,
  reordenar,
  type ResumenLista,
} from "@/lib/lists";

type Dialogo =
  | { tipo: "crear" }
  | { tipo: "renombrar"; lista: ResumenLista }
  | { tipo: "eliminar"; lista: ResumenLista };

// El arrastre (dnd-kit) llega en un chunk aparte. `ListsView` lo pide al
// montarse, en paralelo con `/api/lists/`; si las listas llegan antes, se ve
// el mismo esqueleto que durante su carga.
const cargarGrilla = () => import("@/components/features/lists/SortableListsGrid");
const SortableListsGrid = dynamic(() => cargarGrilla().then((m) => m.SortableListsGrid), {
  ssr: false,
  loading: () => <ListsGridSkeleton />,
});

/**
 * «Lists» según el canvas (L-02). Las tres predeterminadas van fijas arriba;
 * las personalizadas se crean, renombran, eliminan y reordenan. Reordenar se
 * puede con la manija (escritorio), con pulsación larga (celular), con teclado
 * en la manija o con las acciones del menú ⋯ (Move left/right, Move up/down).
 */
export function ListsView() {
  const t = useTranslations();
  const { perfil, error: errorCuenta, recargar } = useAccount();
  const [listas, setListas] = useState<ResumenLista[] | null>(null);
  const [fallo, setFallo] = useState(false);
  const [intento, setIntento] = useState(0);
  const [dialogo, setDialogo] = useState<Dialogo | null>(null);
  const pedidoOrden = useRef(0);

  useEffect(() => {
    void cargarGrilla();
  }, []);

  useEffect(() => {
    if (!perfil?.pk) return;
    let vigente = true;
    setFallo(false);
    apiFetch<ResumenLista[]>("/api/lists/").then(
      (datos) => vigente && setListas(datos),
      () => vigente && setFallo(true)
    );
    return () => {
      vigente = false;
    };
  }, [perfil?.pk, intento]);

  const propias = listas ? personalizadas(listas) : [];
  const fijas = listas ? listas.filter(esPredeterminada) : [];

  async function moverA(desde: number, hacia: number) {
    if (!listas || desde === hacia) return;
    const ids = reordenar(listas, desde, hacia);
    const previas = listas;
    const id = ++pedidoOrden.current;
    setListas(aplicarOrden(listas, ids));
    try {
      const actualizadas = await apiFetch<ResumenLista[]>("/api/lists/order/", {
        method: "PUT",
        body: { ids },
      });
      if (id !== pedidoOrden.current) return;
      setListas(actualizadas);
    } catch (motivo) {
      if (id !== pedidoOrden.current) return;
      setListas(previas);
      toast.error(mensajeDeError(motivo));
    }
  }

  async function crear(nombre: string) {
    const nueva = await apiFetch<ResumenLista>("/api/lists/", {
      method: "POST",
      body: { nombre },
    });
    setListas((actual) => (actual ? [...actual, nueva] : [nueva]));
    setDialogo(null);
    toast.success(t("lists.feedback.created"));
  }

  async function renombrar(lista: ResumenLista, nombre: string) {
    const actualizada = await apiFetch<ResumenLista>(`/api/lists/${lista.id}/`, {
      method: "PUT",
      body: { nombre },
    });
    setListas(
      (actual) =>
        actual?.map((otra) => (otra.id === lista.id ? { ...otra, ...actualizada } : otra)) ?? actual
    );
    setDialogo(null);
    toast.success(t("lists.feedback.renamed"));
  }

  async function eliminar(lista: ResumenLista) {
    await apiFetch(`/api/lists/${lista.id}/`, { method: "DELETE" });
    setListas((actual) => actual?.filter((otra) => otra.id !== lista.id) ?? actual);
    setDialogo(null);
    toast.success(t("lists.feedback.deleted"));
  }

  function accionesDe(lista: ResumenLista, indice: number): AccionLista[] {
    const primera = indice === 0;
    const ultima = indice === propias.length - 1;
    return [
      {
        id: "rename",
        etiqueta: t("common.lists.rename"),
        onSelect: () => setDialogo({ tipo: "renombrar", lista }),
      },
      {
        id: "move-left",
        etiqueta: t("common.lists.moveLeft"),
        solo: "escritorio",
        deshabilitada: primera,
        onSelect: () => void moverA(indice, indice - 1),
      },
      {
        id: "move-right",
        etiqueta: t("common.lists.moveRight"),
        solo: "escritorio",
        deshabilitada: ultima,
        onSelect: () => void moverA(indice, indice + 1),
      },
      {
        id: "move-up",
        etiqueta: t("common.lists.moveUp"),
        solo: "celular",
        deshabilitada: primera,
        onSelect: () => void moverA(indice, indice - 1),
      },
      {
        id: "move-down",
        etiqueta: t("common.lists.moveDown"),
        solo: "celular",
        deshabilitada: ultima,
        onSelect: () => void moverA(indice, indice + 1),
      },
      {
        id: "delete",
        etiqueta: t("common.actions.delete"),
        destructiva: true,
        onSelect: () => setDialogo({ tipo: "eliminar", lista }),
      },
    ];
  }

  const cargando = listas === null && !fallo && !errorCuenta;

  return (
    <main
      id="contenido"
      className="mx-auto flex max-w-[1360px] flex-col gap-6 px-5 pt-4 pb-[120px] md:gap-10 md:px-10 md:pt-12 md:pb-24"
    >
      <div className="flex flex-col gap-2 md:gap-3">
        <h1 className="font-display text-[48px] leading-none md:text-[72px] md:leading-[0.95]">
          {t("nav.main.lists")}
        </h1>
        {listas && (
          <p className="text-fg-2">
            {t("lists.count.summary", { count: listas.length, defaultCount: fijas.length })}
          </p>
        )}
      </div>

      {errorCuenta ? (
        <ErrorRetry mensaje={errorCuenta} onReintentar={() => void recargar()} boton="pildora" />
      ) : fallo ? (
        <ErrorRetry
          mensaje={t("lists.overview.loadError")}
          onReintentar={() => setIntento((anterior) => anterior + 1)}
          boton="pildora"
        />
      ) : cargando ? (
        <ListsGridSkeleton etiqueta={t("lists.overview.loading")} />
      ) : (
        listas && (
          <SortableListsGrid
            fijas={fijas}
            propias={propias}
            accionesDe={accionesDe}
            onMover={(desde, hacia) => void moverA(desde, hacia)}
            onCrear={() => setDialogo({ tipo: "crear" })}
          />
        )
      )}

      {dialogo?.tipo === "crear" && (
        <ListNameDialog modo="crear" onSubmit={crear} onClose={() => setDialogo(null)} />
      )}
      {dialogo?.tipo === "renombrar" && (
        <ListNameDialog
          modo="renombrar"
          inicial={dialogo.lista.nombre}
          onSubmit={(nombre) => renombrar(dialogo.lista, nombre)}
          onClose={() => setDialogo(null)}
        />
      )}
      {dialogo?.tipo === "eliminar" && (
        <ConfirmDialog
          titulo={t("lists.delete.confirmTitle", { listName: dialogo.lista.nombre })}
          descripcion={t("lists.delete.confirmDescription")}
          confirmar={t("common.actions.delete")}
          onConfirm={() => eliminar(dialogo.lista)}
          onCancel={() => setDialogo(null)}
        />
      )}
    </main>
  );
}
