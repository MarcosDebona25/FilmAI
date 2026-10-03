"use client";

import Image from "next/image";
import { useState } from "react";
import type { AvatarOption } from "@/components/AccountProvider";
import { Modal } from "@/components/Modal";
import { Button } from "@/components/ui/button";

/** La selección temporal solo sale del modal cuando se confirma Guardar. */
export function AvatarSelector({
  avatares,
  avatarId,
  onSave,
  onClose,
}: {
  avatares: AvatarOption[];
  avatarId: number;
  onSave: (id: number) => void;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState(avatarId);
  return (
    <Modal title="Elegí un avatar" onClose={onClose}>
      <fieldset className="mt-4">
        <legend className="sr-only">Avatares disponibles</legend>
        <div className="grid grid-cols-4 gap-3 sm:grid-cols-6">
          {avatares.map((avatar) => (
            <label
              key={avatar.id}
              className="relative aspect-square cursor-pointer rounded-full p-1 focus-within:outline-2 focus-within:outline-ring has-[:checked]:bg-primary/20 has-[:checked]:ring-2 has-[:checked]:ring-primary"
            >
              <input
                type="radio"
                name="avatar_id"
                value={avatar.id}
                checked={selected === avatar.id}
                onChange={() => setSelected(avatar.id)}
                className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
                aria-label={`Avatar ${avatar.id}`}
              />
              <div className="relative h-full w-full overflow-hidden rounded-full">
                <Image
                  src={avatar.src}
                  alt=""
                  fill
                  sizes="(max-width: 640px) 25vw, 16vw"
                  className="object-cover"
                />
              </div>
            </label>
          ))}
        </div>
      </fieldset>
      <div className="mt-5 flex justify-end gap-3">
        <Button type="button" className="min-h-11" variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="button" className="min-h-11" onClick={() => onSave(selected)}>
          Guardar
        </Button>
      </div>
    </Modal>
  );
}
