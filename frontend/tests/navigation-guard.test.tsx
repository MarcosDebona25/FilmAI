import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { NavigationGuard, useNavigationGuard } from "@/components/NavigationGuard";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";
import { render, screen } from "./render";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

function Formulario({ onExit }: { onExit: () => void }) {
  const { setDirty, requestExit } = useNavigationGuard();
  return (
    <>
      <button type="button" onClick={() => setDirty(true)}>
        dirty
      </button>
      <button type="button" onClick={() => requestExit(onExit)}>
        exit
      </button>
    </>
  );
}

describe("aviso de salir sin guardar", () => {
  it.each([
    ["en", en],
    ["es", es],
  ] as const)("usa la copia del catálogo en %s", async (locale, copy) => {
    const onExit = vi.fn();
    const user = userEvent.setup();
    render(
      <NavigationGuard>
        <Formulario onExit={onExit} />
      </NavigationGuard>,
      { locale }
    );

    await user.click(screen.getByRole("button", { name: "dirty" }));
    await user.click(screen.getByRole("button", { name: "exit" }));

    expect(screen.getByRole("dialog", { name: copy.profile.leaveDialog.title })).toBeVisible();
    expect(screen.getByText(copy.profile.leaveDialog.body)).toBeVisible();
    await user.click(screen.getByRole("button", { name: copy.profile.leaveDialog.keepEditing }));
    expect(onExit).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "exit" }));
    await user.click(screen.getByRole("button", { name: copy.profile.leaveDialog.leave }));
    expect(onExit).toHaveBeenCalledOnce();
  });
});
