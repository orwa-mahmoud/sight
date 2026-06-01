import { render, screen, act } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { describe, it, expect, beforeEach } from "vitest";

import i18n, { dirFor } from "@shared/i18n";
import { LanguageSwitcher } from "@shared/components/LanguageSwitcher";

describe("i18n", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("maps languages to text direction", () => {
    expect(dirFor("en")).toBe("ltr");
    expect(dirFor("ar")).toBe("rtl");
    expect(dirFor("unknown")).toBe("ltr");
  });

  it("returns the English translation by default", () => {
    expect(i18n.t("nav.conversations")).toBe("Conversations");
  });

  it("returns the Arabic translation after switching", async () => {
    await act(async () => {
      await i18n.changeLanguage("ar");
    });
    expect(i18n.t("nav.conversations")).toBe("المحادثات");
    expect(dirFor(i18n.resolvedLanguage ?? "en")).toBe("rtl");
  });

  it("renders both language options in the switcher", () => {
    render(
      <MantineProvider>
        <LanguageSwitcher />
      </MantineProvider>
    );
    expect(screen.getByLabelText("Language")).toBeInTheDocument();
  });
});
