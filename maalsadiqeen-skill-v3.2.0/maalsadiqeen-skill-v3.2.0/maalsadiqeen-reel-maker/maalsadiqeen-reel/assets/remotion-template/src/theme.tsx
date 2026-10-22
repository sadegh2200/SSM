import React, { createContext, useContext } from "react";
import type { Palette } from "./types";

export const W = 1080;
export const H = 1920;

/**
 * Paper, green, gold — the maalsadiqeen look. Tokens follow references/brand.md (the single source of
 * truth for both engines). Override any token via content.brand.palette.
 * "maroon" is kept as a token name for the warning clause, but the brand never uses red: it maps to a
 * deep gold-ink so the clause reads as emphasis, not alarm.
 */
export const DEFAULT_PALETTE: Palette = {
  bgCenter: "#F4EFE6",
  bgMid: "#EBE4D7",
  bgEdge: "#DDD4C3",
  ink: "#2D2B27",
  inkSoft: "#5A5650",
  green: "#1F4A35",
  olive: "#8AA58F",
  oliveSoft: "#B5C6B8",
  gold: "#957238",
  goldSoft: "#CDB078",
  maroon: "#7A5A24",
  chip: "#E7EEE6",
};

export const F = {
  /** display naskh (headings, hooks, lightly vocalised text) */
  naskh: "Amiri, 'Noto Naskh Arabic', serif",
  /** fully vocalised text ≥ 56px — tighter, clearer mark placement */
  noto: "'Noto Naskh Arabic', Amiri, serif",
  /** UI / explanatory text */
  sans: "Vazirmatn, 'Noto Sans Arabic', sans-serif",
};

const Ctx = createContext<Palette>(DEFAULT_PALETTE);

export const ThemeProvider: React.FC<{
  palette?: Partial<Palette>;
  children: React.ReactNode;
}> = ({ palette, children }) => (
  <Ctx.Provider value={{ ...DEFAULT_PALETTE, ...(palette ?? {}) }}>
    {children}
  </Ctx.Provider>
);

export const useTheme = () => useContext(Ctx);
