import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { AvatarSelector } from "@/components/AvatarSelector";
const avatars = [
  { id: 1, src: "/one.png" },
  { id: 2, src: "/two.png" },
];
it("seleccionar es temporal y solo Guardar confirma el avatar", async () => {
  const save = vi.fn();
  render(<AvatarSelector avatares={avatars} avatarId={1} onSave={save} onClose={vi.fn()} />);
  expect(screen.getAllByText("Elegí un avatar")).toHaveLength(1);
  await userEvent.click(screen.getByRole("radio", { name: "Avatar 2" }));
  expect(screen.getByRole("radio", { name: "Avatar 2" })).toBeChecked();
  expect(save).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
  expect(save).toHaveBeenCalledWith(2);
});
it("cancelar descarta la selección y reabrir precarga el avatar confirmado", async () => {
  const save = vi.fn();
  const close = vi.fn();
  const view = render(
    <AvatarSelector avatares={avatars} avatarId={1} onSave={save} onClose={close} />
  );
  await userEvent.click(screen.getByRole("radio", { name: "Avatar 2" }));
  await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(save).not.toHaveBeenCalled();
  expect(close).toHaveBeenCalledOnce();
  view.unmount();
  render(<AvatarSelector avatares={avatars} avatarId={1} onSave={save} onClose={close} />);
  expect(screen.getByRole("radio", { name: "Avatar 1" })).toBeChecked();
});
it("Escape cierra sin confirmar la selección temporal", async () => {
  const save = vi.fn();
  const close = vi.fn();
  render(<AvatarSelector avatares={avatars} avatarId={1} onSave={save} onClose={close} />);
  await userEvent.click(screen.getByRole("radio", { name: "Avatar 2" }));
  fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
  expect(close).toHaveBeenCalledOnce();
  expect(save).not.toHaveBeenCalled();
});
