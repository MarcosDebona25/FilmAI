"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, Settings, Star, User } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { useAccount } from "@/components/AccountProvider";
import { Avatar } from "@/components/Avatar";
import { ApiError, apiFetch } from "@/lib/api";
import { mantenerFocoEnDialogo } from "@/lib/dialog-focus";
import { translateError } from "@/lib/errors";
import { routes } from "@/lib/routes";

const itemClass =
  "flex h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-[15px] font-medium text-foreground no-underline hover:bg-raised-2 focus-visible:bg-raised-2 focus-visible:outline-2 focus-visible:outline-ring";

/** Menú de la cuenta (avatar → perfil, reseñas, preferencias, cerrar sesión). */
export function AccountMenu() {
  const t = useTranslations("nav");
  const common = useTranslations("common.actions");
  const router = useRouter();
  const { perfil, avatares, limpiar } = useAccount();
  const [menuAbierto, setMenuAbierto] = useState(false);
  const [confirmarLogout, setConfirmarLogout] = useState(false);
  const [saliendo, setSaliendo] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const firstItemRef = useRef<HTMLAnchorElement>(null);
  const cancelarRef = useRef<HTMLButtonElement>(null);
  const logoutDialogRef = useRef<HTMLDivElement>(null);

  function cerrarLogout() {
    setConfirmarLogout(false);
    menuButtonRef.current?.focus();
  }

  useEffect(() => {
    if (!menuAbierto) return;
    firstItemRef.current?.focus();
    function onClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuAbierto(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setMenuAbierto(false);
        menuButtonRef.current?.focus();
      } else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
        const items = Array.from(
          menuRef.current?.querySelectorAll<HTMLElement>("[role='menuitem']") ?? []
        );
        if (!items.length) return;
        e.preventDefault();
        const actual = items.indexOf(document.activeElement as HTMLElement);
        const siguiente =
          e.key === "Home"
            ? 0
            : e.key === "End"
              ? items.length - 1
              : e.key === "ArrowDown"
                ? (actual + 1) % items.length
                : (actual - 1 + items.length) % items.length;
        items[siguiente].focus();
      }
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuAbierto]);

  useEffect(() => {
    if (!confirmarLogout) return;
    cancelarRef.current?.focus();
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") cerrarLogout();
      mantenerFocoEnDialogo(e, logoutDialogRef.current);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [confirmarLogout]);

  if (!perfil) return null;

  async function logout() {
    setSaliendo(true);
    try {
      await apiFetch("/api/auth/logout/", { method: "POST" });
      limpiar();
      setConfirmarLogout(false);
      router.push(routes.home);
    } catch (err) {
      // La sesión sigue activa: se avisa y se permite reintentar.
      toast.error(err instanceof ApiError ? err.message : translateError({ code: "unknown" }));
    } finally {
      setSaliendo(false);
    }
  }

  const nombreCompleto = `${perfil.nombre} ${perfil.apellido}`.trim();

  return (
    <>
      <div className="relative" ref={menuRef}>
        <button
          ref={menuButtonRef}
          type="button"
          onClick={() => setMenuAbierto((v) => !v)}
          aria-haspopup="menu"
          aria-expanded={menuAbierto}
          aria-label={t("account.userMenuLabel", { name: nombreCompleto })}
          className="flex size-11 cursor-pointer items-center justify-center rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          <Avatar perfil={perfil} avatares={avatares} size={40} />
        </button>
        {menuAbierto && (
          <div
            role="menu"
            aria-label={t("account.optionsLabel")}
            className="absolute top-[54px] right-0 z-40 flex w-[280px] max-w-[calc(100vw-24px)] flex-col rounded-[14px] bg-raised p-2 shadow-[0_18px_46px_rgb(0_0_0/0.45),inset_0_0_0_1px_var(--line)]"
          >
            <div className="flex items-center gap-3 px-3 pt-2.5 pb-3.5">
              <span aria-hidden="true" className="flex">
                <Avatar perfil={perfil} avatares={avatares} size={40} />
              </span>
              <span className="flex min-w-0 flex-col">
                <span className="truncate font-semibold text-foreground">{nombreCompleto}</span>
                <span className="truncate text-[13px] text-fg-3">@{perfil.nombre_usuario}</span>
              </span>
            </div>
            <span aria-hidden="true" className="mx-1 mb-1.5 h-px bg-line" />
            <Link
              ref={firstItemRef}
              href={routes.profile}
              role="menuitem"
              onClick={() => setMenuAbierto(false)}
              className={itemClass}
            >
              <User aria-hidden="true" className="size-[18px] text-fg-2" />
              {t("main.profile")}
            </Link>
            <Link
              href={routes.myReviews}
              role="menuitem"
              onClick={() => setMenuAbierto(false)}
              className={itemClass}
            >
              <Star aria-hidden="true" className="size-[18px] text-fg-2" />
              {t("main.ratingsReviews")}
            </Link>
            <Link
              href={routes.settings}
              role="menuitem"
              onClick={() => setMenuAbierto(false)}
              className={itemClass}
            >
              <Settings aria-hidden="true" className="size-[18px] text-fg-2" />
              {t("main.settings")}
            </Link>
            <span aria-hidden="true" className="mx-1 my-1.5 h-px bg-line" />
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setMenuAbierto(false);
                setConfirmarLogout(true);
              }}
              className={`${itemClass} cursor-pointer font-semibold text-destructive`}
            >
              <LogOut aria-hidden="true" className="size-[18px]" />
              {t("account.logOut")}
            </button>
          </div>
        )}
      </div>

      {confirmarLogout && (
        <div
          ref={logoutDialogRef}
          className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget && !saliendo) cerrarLogout();
          }}
        >
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="titulo-cerrar-sesion"
            aria-describedby="descripcion-cerrar-sesion"
            className="flex w-full max-w-[420px] flex-col gap-3.5 rounded-2xl bg-raised p-[26px] shadow-[0_30px_80px_rgb(0_0_0/0.5)]"
          >
            <h2
              id="titulo-cerrar-sesion"
              className="font-display text-[34px] leading-none text-foreground"
            >
              {t("account.logoutConfirmTitle")}
            </h2>
            <p id="descripcion-cerrar-sesion" className="text-fg-2">
              {t("account.logoutConfirmDescription")}
            </p>
            <div className="mt-1.5 flex justify-end gap-2.5">
              <button
                ref={cancelarRef}
                type="button"
                onClick={cerrarLogout}
                disabled={saliendo}
                className="h-12 cursor-pointer rounded-[10px] px-4 font-medium text-fg-2 hover:text-foreground disabled:cursor-wait"
              >
                {common("cancel")}
              </button>
              <button
                type="button"
                onClick={logout}
                disabled={saliendo}
                className="h-12 cursor-pointer rounded-[10px] bg-raised-2 px-5 font-semibold text-foreground hover:brightness-110 disabled:cursor-wait disabled:opacity-70"
              >
                {t("account.logOut")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
