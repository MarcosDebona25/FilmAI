"use client";

import Image from "next/image";
import { useState } from "react";

import type { AvatarOption, Perfil } from "@/components/AccountProvider";

export function Avatar({
  perfil,
  avatares,
  size = 40,
}: {
  perfil: Perfil;
  avatares: AvatarOption[];
  size?: number;
}) {
  const [srcFallida, setSrcFallida] = useState<string | null>(null);
  const avatar = avatares.find((item) => item.id === perfil.avatar_id);
  const iniciales = `${perfil.nombre.charAt(0)}${perfil.apellido.charAt(0)}`.toUpperCase() || "?";

  if (!avatar || srcFallida === avatar.src) {
    return (
      <span
        className="flex shrink-0 items-center justify-center rounded-full bg-primary font-semibold text-primary-foreground"
        style={{ width: size, height: size }}
        aria-label={`Avatar de ${perfil.nombre} ${perfil.apellido}`}
      >
        {iniciales}
      </span>
    );
  }

  return (
    <Image
      src={avatar.src}
      alt={`Avatar de ${perfil.nombre} ${perfil.apellido}`}
      width={size}
      height={size}
      onError={() => setSrcFallida(avatar.src)}
      className="shrink-0 rounded-full object-cover"
    />
  );
}
