import { MantineProvider, useComputedColorScheme } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ColorSchemeToggle } from "./ColorSchemeToggle";

function Probe() {
  const scheme = useComputedColorScheme("light");
  return <span data-testid="scheme">{scheme}</span>;
}

describe("ColorSchemeToggle", () => {
  it("toggles the Mantine color scheme", () => {
    render(
      <MantineProvider defaultColorScheme="light">
        <ColorSchemeToggle />
        <Probe />
      </MantineProvider>,
    );
    expect(screen.getByTestId("scheme")).toHaveTextContent("light");
    fireEvent.click(screen.getByLabelText("Toggle color scheme"));
    expect(screen.getByTestId("scheme")).toHaveTextContent("dark");
    fireEvent.click(screen.getByLabelText("Toggle color scheme"));
    expect(screen.getByTestId("scheme")).toHaveTextContent("light");
  });
});
