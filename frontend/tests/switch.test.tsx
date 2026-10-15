import { describe, expect, it, vi } from "vitest";

import { Switch } from "@/components/ui/switch";
import { fireEvent, render, screen } from "./render";

describe("Switch", () => {
  it("anuncia su estado y su nombre, y avisa el cambio", () => {
    const onChange = vi.fn();
    render(
      <>
        <span id="etiqueta">Weekly recommendations</span>
        <Switch checked={false} onChange={onChange} labelledBy="etiqueta" />
      </>
    );

    const interruptor = screen.getByRole("switch", { name: "Weekly recommendations" });
    expect(interruptor).toHaveAttribute("aria-checked", "false");
    fireEvent.click(interruptor);

    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("apagado mientras guarda no avisa nada", () => {
    const onChange = vi.fn();
    render(<Switch checked onChange={onChange} labelledBy="x" disabled />);

    fireEvent.click(screen.getByRole("switch"));

    expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "true");
    expect(onChange).not.toHaveBeenCalled();
  });
});
