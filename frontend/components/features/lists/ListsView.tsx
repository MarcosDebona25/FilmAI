"use client";

import { useRef, useState } from "react";
import { useEffect } from "react";
import {
  DndContext,
  KeyboardSensor,
  closestCenter,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { useAccount } from "@/components/AccountProvider";
import type { AccionLista } from "@/components/features/lists/ListActionsMenu";
import { ListCard, useNombreLista } from "@/components/features/lists/ListCard";
import { ListNameDialog } from "@/components/features/lists/ListNameDialog";
import { ConfirmDialog } from "@/components/features/title/ConfirmDialog";
import { mensajeDeError } from "@/components/features/title/RatingDialog";
import { ErrorRetry } from "@/components/ui/ErrorRetry";
import { apiFetch } from "@/lib/api";
import { useFormats } from "@/lib/format";
import {
  DISTANCIA_MANIJA_PX,
  ESPERA_ARRASTRE_MS,
  ManijaSensor,
  PulsacionLargaSensor,
  TOLERANCIA_ARRASTRE_PX,
} from "@/lib/list-sensors";
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

function TarjetaOrdenable({ lista, acciones }: { lista: ResumenLista; acciones: AccionLista[] }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: lista.id });
  return (
    <ListCard
      lista={lista}
      acciones={acciones}
      arrastre={{
        refNodo: setNodeRef,
        refManija: setActivatorNodeRef,
        atributos: attributes,
        escuchas: listeners,
        estilo: { transform: CSS.Transform.toString(transform), transition },
        arrastrando: isDragging,
      }}
    />
  );
}

/**
 * «Lists» según el canvas (L-02). Las tres predeterminadas van fijas arriba;
 * las personalizadas se crean, renombran, eliminan y reordenan. Reordenar se
 * puede con la manija (escritorio), con pulsación larga (celular), con teclado
 * en la manija o con las acciones del menú ⋯ (Move left/right, Move up/down).
 */
export function ListsView() {
  const t = useTranslations();
  const { perfil, error: errorCuenta, recargar } = useAccount();
  const nombreDe = useNombreLista();
  const formats = useFormats();
  const [listas, setListas] = useState<ResumenLista[] | null>(null);
  const [fallo, setFallo] = useState(false);
  const [intento, setIntento] = useState(0);
  const [dialogo, setDialogo] = useState<Dialogo | null>(null);
  const pedidoOrden = useRef(0);

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

  const sensores = useSensors(
    useSensor(ManijaSensor, { activationConstraint: { distance: DISTANCIA_MANIJA_PX } }),
    useSensor(PulsacionLargaSensor, {
      activationConstraint: { delay: ESPERA_ARRASTRE_MS, tolerance: TOLERANCIA_ARRASTRE_PX },
    }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

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

  function alSoltar({ active, over }: DragEndEvent) {
    if (!over || active.id === over.id) return;
    const desde = propias.findIndex((lista) => lista.id === active.id);
    const hacia = propias.findIndex((lista) => lista.id === over.id);
    if (desde >= 0 && hacia >= 0) void moverA(desde, hacia);
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

  const anuncios: Announcements = {
    onDragStart({ active }) {
      const indice = propias.findIndex((lista) => lista.id === active.id);
      return t("lists.reorder.pickedUp", {
        listName: indice >= 0 ? nombreDe(propias[indice]) : "",
        position: formats.number(indice + 1),
        total: formats.number(propias.length),
      });
    },
    onDragOver({ active, over }) {
      if (!over) return undefined;
      const indice = propias.findIndex((lista) => lista.id === over.id);
      const propia = propias.find((lista) => lista.id === active.id);
      return t("lists.reorder.movedTo", {
        listName: propia ? nombreDe(propia) : "",
        position: formats.number(indice + 1),
        total: formats.number(propias.length),
      });
    },
    onDragEnd({ active, over }) {
      const propia = propias.find((lista) => lista.id === active.id);
      const indice = propias.findIndex((lista) => lista.id === (over ?? active).id);
      return t("lists.reorder.dropped", {
        listName: propia ? nombreDe(propia) : "",
        position: formats.number(indice + 1),
        total: formats.number(propias.length),
      });
    },
    onDragCancel({ active }) {
      const indice = propias.findIndex((lista) => lista.id === active.id);
      return t("lists.reorder.cancelled", {
        listName: indice >= 0 ? nombreDe(propias[indice]) : "",
        position: formats.number(indice + 1),
      });
    },
  };

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
        <ul
          role="status"
          aria-label={t("lists.overview.loading")}
          className="grid grid-cols-1 gap-4 md:grid-cols-[repeat(auto-fill,minmax(min(380px,100%),1fr))] md:gap-5"
        >
          {[0, 1, 2].map((indice) => (
            <li
              key={indice}
              className="h-[188px] rounded-2xl bg-raised motion-safe:animate-pulse md:h-[236px]"
            />
          ))}
        </ul>
      ) : (
        listas && (
          <DndContext
            sensors={sensores}
            collisionDetection={closestCenter}
            onDragEnd={alSoltar}
            accessibility={{
              announcements: anuncios,
              screenReaderInstructions: { draggable: t("lists.reorder.instructions") },
            }}
          >
            <SortableContext
              items={propias.map((lista) => lista.id)}
              strategy={rectSortingStrategy}
            >
              <ul className="grid grid-cols-1 gap-4 md:grid-cols-[repeat(auto-fill,minmax(min(380px,100%),1fr))] md:gap-5">
                {fijas.map((lista) => (
                  <ListCard key={lista.id} lista={lista} />
                ))}
                {propias.map((lista, indice) => (
                  <TarjetaOrdenable
                    key={lista.id}
                    lista={lista}
                    acciones={accionesDe(lista, indice)}
                  />
                ))}
                <li className="list-none">
                  <button
                    type="button"
                    onClick={() => setDialogo({ tipo: "crear" })}
                    className="flex h-16 w-full cursor-pointer items-center justify-center gap-2.5 rounded-2xl border border-dashed border-line font-semibold text-fg-2 hover:border-fg-3 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring md:h-full md:min-h-[236px] md:flex-col"
                  >
                    <Plus aria-hidden="true" className="size-6 text-primary" />
                    {t("lists.create.title")}
                  </button>
                </li>
              </ul>
            </SortableContext>
          </DndContext>
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
