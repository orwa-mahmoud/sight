import { createTheme, type MantineColorsTuple } from "@mantine/core";

// Coral / sunrise — distinctive from PropertyBot's defaults, friendly to
// the "front desk" metaphor without being aggressively branded.
const coral: MantineColorsTuple = [
  "#fff3ed",
  "#ffe2d3",
  "#fdc2a7",
  "#fba076",
  "#f9844c",
  "#f87330",
  "#f76b22",
  "#dc5915",
  "#c44e10",
  "#aa4109",
];

// Deep slate as accent — provides contrast for headings and active nav.
const slate: MantineColorsTuple = [
  "#f3f5f8",
  "#e3e6eb",
  "#c5cbd5",
  "#a4adbd",
  "#88949f",
  "#717f97",
  "#67768f",
  "#566480",
  "#4d5a73",
  "#404c66",
];

export const theme = createTheme({
  primaryColor: "coral",
  primaryShade: { light: 6, dark: 5 },
  defaultRadius: "md",
  // 'IBM Plex Sans Arabic' (self-hosted via @fontsource) covers Arabic glyphs
  // for RTL; Latin text falls through to the system stack ahead of it.
  fontFamily:
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Helvetica Neue', 'IBM Plex Sans Arabic', sans-serif",
  headings: {
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Helvetica Neue', 'IBM Plex Sans Arabic', sans-serif",
    fontWeight: "600",
  },
  colors: {
    coral,
    slate,
  },
  components: {
    Button: {
      defaultProps: {
        fw: 500,
      },
    },
  },
});
