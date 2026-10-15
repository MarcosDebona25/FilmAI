"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Modal } from "@/components/Modal";
import { Button } from "@/components/ui/button";

type Guard = { setDirty: (dirty: boolean) => void; requestExit: (action: () => void) => void };
const Context = createContext<Guard | null>(null);
const KEY = "filmaiHistoryIndex";

/** Índices en history.state permiten revertir y repetir atrás/adelante sin perder su destino. */
export function NavigationGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const t = useTranslations("profile.leaveDialog");
  const dirty = useRef(false);
  const pending = useRef<(() => void) | null>(null);
  const [open, setOpen] = useState(false);
  const setDirty = useCallback((value: boolean) => {
    dirty.current = value;
  }, []);
  const requestExit = useCallback((action: () => void) => {
    if (!dirty.current) {
      action();
      return;
    }
    pending.current = action;
    setOpen(true);
  }, []);

  useEffect(() => {
    const history = window.history;
    const push = history.pushState.bind(history);
    const replace = history.replaceState.bind(history);
    let index = history.state?.[KEY] ?? 0;
    let restoring = false;
    let bypass = false;
    replace({ ...history.state, [KEY]: index }, "");
    history.pushState = (data, unused, url) => {
      const next = index + 1;
      push({ ...data, [KEY]: next }, unused, url);
      index = next;
    };
    history.replaceState = (data, unused, url) => replace({ ...data, [KEY]: index }, unused, url);

    function pop(event: PopStateEvent) {
      const target = event.state?.[KEY];
      if (restoring) {
        restoring = false;
        event.stopImmediatePropagation();
        setOpen(true);
        return;
      }
      if (bypass || !dirty.current || typeof target !== "number") {
        bypass = false;
        if (typeof target === "number") index = target;
        return;
      }
      const delta = target - index;
      if (!delta) return;
      event.stopImmediatePropagation();
      restoring = true;
      pending.current = () => {
        bypass = true;
        history.go(delta);
      };
      history.go(-delta);
    }
    function click(event: MouseEvent) {
      if (
        !dirty.current ||
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      )
        return;
      const link = (event.target as Element)?.closest<HTMLAnchorElement>("a[href]");
      if (!link || link.download || (link.target && link.target !== "_self")) return;
      const url = new URL(link.href);
      if (url.href === window.location.href) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      requestExit(() => {
        if (url.origin === window.location.origin)
          router.push(url.pathname + url.search + url.hash);
        else window.location.assign(url.href);
      });
    }
    function unload(event: BeforeUnloadEvent) {
      if (dirty.current) {
        event.preventDefault();
        event.returnValue = "";
      }
    }
    window.addEventListener("popstate", pop, true);
    document.addEventListener("click", click, true);
    window.addEventListener("beforeunload", unload);
    return () => {
      history.pushState = push;
      history.replaceState = replace;
      window.removeEventListener("popstate", pop, true);
      document.removeEventListener("click", click, true);
      window.removeEventListener("beforeunload", unload);
    };
  }, [requestExit, router]);
  function close() {
    pending.current = null;
    setOpen(false);
  }
  return (
    <Context.Provider value={{ setDirty, requestExit }}>
      {children}
      {open && (
        <Modal title={t("title")} onClose={close}>
          <p className="mt-3">{t("body")}</p>
          <div className="mt-6 flex flex-wrap justify-end gap-3">
            <Button className="min-h-11" variant="secondary" onClick={close}>
              {t("keepEditing")}
            </Button>
            <Button
              className="min-h-11"
              variant="destructive"
              onClick={() => {
                const action = pending.current;
                dirty.current = false;
                close();
                action?.();
              }}
            >
              {t("leave")}
            </Button>
          </div>
        </Modal>
      )}
    </Context.Provider>
  );
}
export function useNavigationGuard() {
  const value = useContext(Context);
  if (!value) throw new Error("Falta NavigationGuard");
  return value;
}
