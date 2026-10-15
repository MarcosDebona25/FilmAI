import { fireEvent, render, screen } from "./render";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { AvatarDialog } from "@/components/features/profile/AvatarDialog";

const avatars = [
  { id: 1, src: "/one.png" },
  { id: 2, src: "/two.png" },
  { id: 3, src: "/three.png" },
];

it("elegir es temporal y solo Guardar confirma el avatar", async () => {
  const save = vi.fn();
  render(<AvatarDialog avatares={avatars} avatarId={1} onSave={save} onClose={vi.fn()} />);

  expect(screen.getByRole("dialog", { name: "Elegí un avatar" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("radio", { name: "Avatar 2" }));
  expect(screen.getByRole("radio", { name: "Avatar 2" })).toHaveAttribute("aria-checked", "true");
  expect(save).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

  expect(save).toHaveBeenCalledWith(2);
});

it("cancelar descarta la elección y reabrir precarga el avatar confirmado", async () => {
  const save = vi.fn();
  const close = vi.fn();
  const view = render(
    <AvatarDialog avatares={avatars} avatarId={1} onSave={save} onClose={close} />
  );
  await userEvent.click(screen.getByRole("radio", { name: "Avatar 2" }));
  await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));

  expect(save).not.toHaveBeenCalled();
  expect(close).toHaveBeenCalledOnce();
  view.unmount();
  render(<AvatarDialog avatares={avatars} avatarId={1} onSave={save} onClose={close} />);
  expect(screen.getByRole("radio", { name: "Avatar 1" })).toHaveAttribute("aria-checked", "true");
});

it("Escape cierra sin confirmar la elección temporal", async () => {
  const save = vi.fn();
  const close = vi.fn();
  render(<AvatarDialog avatares={avatars} avatarId={1} onSave={save} onClose={close} />);
  await userEvent.click(screen.getByRole("radio", { name: "Avatar 2" }));

  fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));

  expect(close).toHaveBeenCalledOnce();
  expect(save).not.toHaveBeenCalled();
});

it("las flechas mueven la elección y el foco (radiogroup)", () => {
  render(<AvatarDialog avatares={avatars} avatarId={1} onSave={vi.fn()} onClose={vi.fn()} />);

  fireEvent.keyDown(screen.getByRole("radio", { name: "Avatar 1" }), { key: "ArrowRight" });
  expect(screen.getByRole("radio", { name: "Avatar 2" })).toHaveAttribute("aria-checked", "true");
  expect(screen.getByRole("radio", { name: "Avatar 2" })).toHaveFocus();
  fireEvent.keyDown(screen.getByRole("radio", { name: "Avatar 1" }), { key: "ArrowLeft" });
  expect(screen.getByRole("radio", { name: "Avatar 3" })).toHaveAttribute("aria-checked", "true");
});
