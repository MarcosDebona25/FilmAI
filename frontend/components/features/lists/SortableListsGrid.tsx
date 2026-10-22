"use client";

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

import type { AccionLista } from "@/components/features/lists/ListActionsMenu";
import { CLASE_GRILLA_LISTAS } from "@/components/features/lists/ListsGridSkeleton";
import { ListCard, useNombreLista } from "@/components/features/lists/ListCard";
import { useFormats } from "@/lib/format";
import {
  DISTANCIA_MANIJA_PX,
  ESPERA_ARRASTRE_MS,
  ManijaSensor,
  PulsacionLargaSensor,
  TOLERANCIA_ARRASTRE_PX,
} from "@/lib/list-sensors";
import type { ResumenLista } from "@/lib/lists";

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
 * La grilla de «Lists» con el arrastre de dnd-kit. Va en su propio módulo para
 * que `ListsView` la cargue con `next/dynamic`: dnd-kit (~16 kB comprimido) se
 * baja junto con las listas y no en el primer JS de la página (22/10/2026).
 */
export function SortableListsGrid({
  fijas,
  propias,
  accionesDe,
  onMover,
  onCrear,
}: {
  fijas: ResumenLista[];
  propias: ResumenLista[];
  accionesDe: (lista: ResumenLista, indice: number) => AccionLista[];
  onMover: (desde: number, hacia: number) => void;
  onCrear: () => void;
}) {
  const t = useTranslations();
  const nombreDe = useNombreLista();
  const formats = useFormats();

  const sensores = useSensors(
    useSensor(ManijaSensor, { activationConstraint: { distance: DISTANCIA_MANIJA_PX } }),
    useSensor(PulsacionLargaSensor, {
      activationConstraint: { delay: ESPERA_ARRASTRE_MS, tolerance: TOLERANCIA_ARRASTRE_PX },
    }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  function alSoltar({ active, over }: DragEndEvent) {
    if (!over || active.id === over.id) return;
    const desde = propias.findIndex((lista) => lista.id === active.id);
    const hacia = propias.findIndex((lista) => lista.id === over.id);
    if (desde >= 0 && hacia >= 0) onMover(desde, hacia);
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

  return (
    <DndContext
      sensors={sensores}
      collisionDetection={closestCenter}
      onDragEnd={alSoltar}
      accessibility={{
        announcements: anuncios,
        screenReaderInstructions: { draggable: t("lists.reorder.instructions") },
      }}
    >
      <SortableContext items={propias.map((lista) => lista.id)} strategy={rectSortingStrategy}>
        <ul className={CLASE_GRILLA_LISTAS}>
          {fijas.map((lista) => (
            <ListCard key={lista.id} lista={lista} />
          ))}
          {propias.map((lista, indice) => (
            <TarjetaOrdenable key={lista.id} lista={lista} acciones={accionesDe(lista, indice)} />
          ))}
          <li className="list-none">
            <button
              type="button"
              onClick={onCrear}
              className="flex h-16 w-full cursor-pointer items-center justify-center gap-2.5 rounded-2xl border border-dashed border-line font-semibold text-fg-2 hover:border-fg-3 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring md:h-full md:min-h-[236px] md:flex-col"
            >
              <Plus aria-hidden="true" className="size-6 text-primary" />
              {t("lists.create.title")}
            </button>
          </li>
        </ul>
      </SortableContext>
    </DndContext>
  );
}
