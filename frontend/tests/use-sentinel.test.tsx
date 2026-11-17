import { render } from "@testing-library/react";
import { useRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ANTICIPO, useSentinel } from "@/lib/use-sentinel";

type Aviso = (entradas: { isIntersecting: boolean }[]) => void;
const creados: { aviso: Aviso; opciones: IntersectionObserverInit; disconnect: () => void }[] = [];
const original = globalThis.IntersectionObserver;

beforeEach(() => {
  creados.length = 0;
  globalThis.IntersectionObserver = class {
    disconnect = vi.fn();
    constructor(aviso: Aviso, opciones: IntersectionObserverInit) {
      creados.push({ aviso, opciones, disconnect: this.disconnect });
    }
    observe() {}
    unobserve() {}
  } as unknown as typeof IntersectionObserver;
});
afterEach(() => {
  globalThis.IntersectionObserver = original;
});

type Props = { activo: boolean; alVer: () => void; margen?: string; reiniciar?: number };
function Prueba({ activo, alVer, margen, reiniciar }: Props) {
  const nodo = useRef<HTMLDivElement>(null);
  useSentinel(nodo, { activo, alVer, margen, reiniciar });
  return <div ref={nodo} />;
}

describe("useSentinel", () => {
  it("observa con el anticipo de 600 px y avisa al cruzarlo", () => {
    const alVer = vi.fn();
    render(<Prueba activo alVer={alVer} />);
    expect(creados).toHaveLength(1);
    expect(creados[0].opciones.rootMargin).toBe(ANTICIPO);
    creados[0].aviso([{ isIntersecting: false }]);
    expect(alVer).not.toHaveBeenCalled();
    creados[0].aviso([{ isIntersecting: true }]);
    expect(alVer).toHaveBeenCalledTimes(1);
  });

  it("inactivo no observa", () => {
    render(<Prueba activo={false} alVer={vi.fn()} />);
    expect(creados).toHaveLength(0);
  });

  it("al desactivarse desconecta el observador", () => {
    const vista = render(<Prueba activo alVer={vi.fn()} />);
    vista.rerender(<Prueba activo={false} alVer={vi.fn()} />);
    expect(creados[0].disconnect).toHaveBeenCalled();
  });

  it("llama siempre a la última función sin recrear el observador", () => {
    const primera = vi.fn();
    const segunda = vi.fn();
    const vista = render(<Prueba activo alVer={primera} />);
    vista.rerender(<Prueba activo alVer={segunda} />);
    expect(creados).toHaveLength(1);
    creados[0].aviso([{ isIntersecting: true }]);
    expect(primera).not.toHaveBeenCalled();
    expect(segunda).toHaveBeenCalledTimes(1);
  });

  it("acepta otro margen y se recrea al cambiar `reiniciar`", () => {
    const vista = render(
      <Prueba activo alVer={vi.fn()} margen="0px 0px 600px 0px" reiniciar={1} />
    );
    expect(creados[0].opciones.rootMargin).toBe("0px 0px 600px 0px");
    vista.rerender(<Prueba activo alVer={vi.fn()} margen="0px 0px 600px 0px" reiniciar={2} />);
    expect(creados).toHaveLength(2);
    expect(creados[0].disconnect).toHaveBeenCalled();
  });
});
