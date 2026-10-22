import { afterEach, describe, expect, it, vi } from "vitest";

import { ListsGridPreload, grillaCargada } from "@/components/features/lists/ListsGridPreload";
import { render, waitFor } from "./render";

const cuenta = vi.hoisted(() => ({ perfil: null as null | { pk: number } }));
vi.mock("@/components/AccountProvider", () => ({ useAccount: () => cuenta }));

afterEach(() => {
  cuenta.perfil = null;
  vi.unstubAllGlobals();
});

describe("precarga de la grilla de Lists", () => {
  // Sin la precarga, la primera entrada a Lists esperaba el chunk de dnd-kit
  // después del JS de la ruta (medido el 22/10/2026).
  it("sin sesión no baja nada", () => {
    const enReposo = vi.fn();
    vi.stubGlobal("requestIdleCallback", enReposo);
    render(<ListsGridPreload />);

    expect(enReposo).not.toHaveBeenCalled();
  });

  it("con sesión, baja la grilla cuando el navegador queda libre", async () => {
    const pendientes: (() => void)[] = [];
    vi.stubGlobal("requestIdleCallback", (tarea: () => void) => pendientes.push(tarea));
    vi.stubGlobal("cancelIdleCallback", vi.fn());
    cuenta.perfil = { pk: 1 };
    const { unmount } = render(<ListsGridPreload />);

    expect(pendientes).toHaveLength(1);
    expect(grillaCargada()).toBeNull();
    pendientes[0]();
    // Queda en memoria: `ListsView` la dibuja sin pasar por un esqueleto.
    await waitFor(() => expect(grillaCargada()).toEqual(expect.any(Function)));
    unmount();
  });
});
