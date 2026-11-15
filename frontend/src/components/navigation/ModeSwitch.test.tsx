import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ModeSwitch } from "./ModeSwitch";

describe("<ModeSwitch>", () => {
  it("marca el modo activo y avisa al elegir el otro", async () => {
    const onChange = vi.fn();
    render(<ModeSwitch mode="explorador" onChange={onChange} />);
    expect(screen.getByRole("button", { name: /explorador/i })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: /científico/i }));
    expect(onChange).toHaveBeenCalledWith("cientifico");
  });
});
