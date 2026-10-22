export type Palette = {
  bgCenter: string;
  bgMid: string;
  bgEdge: string;
  ink: string;
  inkSoft: string;
  green: string;
  olive: string;
  oliveSoft: string;
  gold: string;
  goldSoft: string;
  maroon: string;
  chip: string;
};

export type HadithLine = { t: string; style?: "lead" | "body" | "warning" };

export type Quote = { a?: string; b?: string; lines?: string[]; src?: string };

export type Point = {
  label?: string;
  title: string;
  desc?: string[];
  quote?: Quote;
  chip?: string;
};

export type ChainNode = { name: string; grade?: string; imam?: boolean };

export type Content = {
  slug?: string;
  brand?: {
    handle?: string;
    logo?: string | null;
    branch?: string | null;
    palette?: Partial<Palette>;
  };
  hook: { line1: string; line2?: string; highlight?: string; sub?: string };
  hadith: { intro?: string; lines: HadithLine[]; bridge?: string; /** label shown on continuation pages */ continued?: string };
  points?: Point[];
  bayan?: { title?: string; lines: string[]; emphasis?: number[]; src?: string };
  sanad?: {
    question?: string;
    sub?: string;
    chain?: ChainNode[];
    verdict?: string;
    verdict_sub?: string;
    note?: string;
  };
  sources?: string[];
  cta?: { line1?: string; line2?: string; footer?: string; icons?: boolean };
  audio?: { bed?: boolean; sfx?: boolean; bed_volume?: number };
};

export type SceneId = "hook" | "hadith" | "points" | "bayan" | "sanad" | "cta";

export type HadithPage = {
  from: number;
  dur: number;
  intro_at: number;
  /** y of the text block (px); short pages are nudged toward the optical centre */
  top?: number;
  lines: { i: number; at: number }[];
  bridge_at?: number;
};

export type Plan = {
  fps: number;
  total: number;
  order: SceneId[];
  scenes: {
    hook?: { from: number; dur: number; size: number; sub_at: number };
    hadith?: {
      from: number;
      dur: number;
      body: number;
      lead: number;
      warning: number;
      intro: number;
      pages: HadithPage[];
    };
    points?: {
      from: number;
      dur: number;
      cards: { from: number; dur: number }[];
      title: number;
      desc: number;
    };
    bayan?: { from: number; dur: number; size: number; top?: number; lines_at: number[] };
    sanad?: {
      from: number;
      dur: number;
      start: number;
      step: number;
      seal_at: number;
      row: number;
      name: number;
      chip: number;
    };
    cta?: { from: number; dur: number };
  };
  sfx: { at: number; src: string; vol: number }[];
};

export type ReelProps = { content: Content; plan: Plan };
