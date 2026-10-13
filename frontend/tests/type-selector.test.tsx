import { describe, expect, it, vi } from "vitest";

import { TypeSelector } from "@/components/features/TypeSelector";
import { fireEvent, render, screen } from "./render";

describe("TypeSelector", () => {
  it("marca la opción elegida con aria-pressed", () => {
    render(<TypeSelector value="movie" onChange={vi.fn()} />, { locale: "en" });

    const grupo = screen.getByRole("group", { name: "Content type" });
    expect(grupo).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Movies" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "TV shows" })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
  });

  it("avisa la opción nueva al elegirla", () => {
    const onChange = vi.fn();
    render(<TypeSelector value="all" onChange={onChange} />, { locale: "es" });

    fireEvent.click(screen.getByRole("button", { name: "Series" }));

    expect(onChange).toHaveBeenCalledWith("tv");
  });
});
