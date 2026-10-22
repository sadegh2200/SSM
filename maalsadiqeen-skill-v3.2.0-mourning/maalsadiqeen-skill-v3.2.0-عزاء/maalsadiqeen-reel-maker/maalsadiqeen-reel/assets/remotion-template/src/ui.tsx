import React from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { F, H, W, useTheme } from "./theme";

export const ease = Easing.bezier(0.16, 1, 0.3, 1);
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);
export const pop = Easing.bezier(0.2, 1.3, 0.4, 1);

export const clamp = (
  frame: number,
  from: number,
  to: number,
  out: [number, number],
  easing = ease,
) =>
  interpolate(frame, [from, Math.max(to, from + 1)], out, {
    easing,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

/** Fade + rise + un-blur reveal, timed relative to the enclosing Sequence. */
export const Reveal: React.FC<{
  from: number;
  duration?: number;
  rise?: number;
  blur?: boolean;
  scaleFrom?: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ from, duration = 16, rise = 28, blur = true, scaleFrom = 1, style, children }) => {
  const frame = useCurrentFrame();
  const p = clamp(frame, from, from + duration, [0, 1]);
  const opacity = clamp(frame, from, from + duration * 0.7, [0, 1], Easing.linear);
  return (
    <div
      style={{
        opacity,
        translate: `0px ${(1 - p) * rise}px`,
        scale: String(scaleFrom + (1 - scaleFrom) * p),
        filter: blur ? `blur(${(1 - p) * 10}px)` : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/** Scene wrapper: fades in at its start and out (with a slight upward drift) at its end. */
export const Scene: React.FC<{
  durationInFrames: number;
  fadeIn?: number;
  fadeOut?: number;
  children: React.ReactNode;
}> = ({ durationInFrames, fadeIn = 10, fadeOut = 12, children }) => {
  const frame = useCurrentFrame();
  const inO = fadeIn > 0 ? clamp(frame, 0, fadeIn, [0, 1], Easing.linear) : 1;
  const outO = clamp(frame, durationInFrames - fadeOut, durationInFrames, [1, 0], Easing.linear);
  const drift = clamp(frame, durationInFrames - fadeOut, durationInFrames, [0, -18], easeInOut);
  return (
    <AbsoluteFill style={{ opacity: Math.min(inO, outO), translate: `0px ${drift}px`, direction: "rtl" }}>
      {children}
    </AbsoluteFill>
  );
};

/** Paper background: radial gradient + soft grain + slow breathing zoom. */
export const Paper: React.FC = () => {
  const C = useTheme();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const s = interpolate(frame, [0, durationInFrames], [1, 1.035]);
  return (
    <AbsoluteFill style={{ backgroundColor: C.bgEdge }}>
      <AbsoluteFill
        style={{
          scale: String(s),
          background: `radial-gradient(ellipse 70% 55% at 50% 46%, ${C.bgCenter} 0%, ${C.bgMid} 45%, ${C.bgEdge} 100%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `url(${staticFile("img/noise.png")})`,
          backgroundSize: "512px 512px",
          opacity: 0.07,
          mixBlendMode: "multiply",
        }}
      />
    </AbsoluteFill>
  );
};

/** Persistent brand frame: branch (top-right), logo or handle (top-left), vertical rule (right). */
export const BrandFrame: React.FC<{
  logo?: string | null;
  branch?: string | null;
  handle?: string;
  total: number;
}> = ({ logo, branch, handle, total }) => {
  const C = useTheme();
  const frame = useCurrentFrame();
  const o = Math.min(
    clamp(frame, 6, 30, [0, 1], Easing.linear),
    clamp(frame, total - 16, total, [1, 0], Easing.linear),
  );
  const rule = clamp(frame, 10, 70, [0, 1]);
  const x = W - 86;
  const top = 300;
  const bottom = H - 300;
  const len = (bottom - top) * rule;
  return (
    <AbsoluteFill style={{ opacity: o, pointerEvents: "none" }}>
      {branch ? (
        <Img src={staticFile(branch)} style={{ position: "absolute", right: 48, top: 128, width: 100 }} />
      ) : null}
      {logo ? (
        <Img src={staticFile(logo)} style={{ position: "absolute", left: 56, top: 132, width: 250 }} />
      ) : handle ? (
        <div
          style={{
            position: "absolute",
            left: 60,
            top: 140,
            fontFamily: "Georgia, serif",
            fontSize: 30,
            letterSpacing: 1,
            color: C.inkSoft,
            direction: "ltr",
          }}
        >
          {handle}
        </div>
      ) : null}
      <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0 }}>
        <line x1={x} y1={top} x2={x} y2={top + len} stroke={C.oliveSoft} strokeWidth={2} />
        {[0.12, 0.5, 0.88].map((p, i) => {
          const y = top + (bottom - top) * p;
          const show = len >= (bottom - top) * p;
          return (
            <rect
              key={i}
              x={x - 6}
              y={y - 6}
              width={12}
              height={12}
              fill={C.bgCenter}
              stroke={C.olive}
              strokeWidth={1.5}
              transform={`rotate(45 ${x} ${y})`}
              opacity={show ? 1 : 0}
            />
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};

/** Arc-and-stars ornament, drawn on with stroke animation. */
export const ArcOrnament: React.FC<{ from: number; width?: number; style?: React.CSSProperties }> = ({
  from,
  width = 820,
  style,
}) => {
  const C = useTheme();
  const frame = useCurrentFrame();
  const draw = clamp(frame, from, from + 40, [0, 1], easeInOut);
  const dots = clamp(frame, from + 14, from + 48, [0, 1], Easing.linear);
  const star = clamp(frame, from + 30, from + 52, [0, 1]);
  const twinkle = 0.75 + 0.25 * Math.sin((frame - from) / 7);
  const q = (p0: [number, number], p1: [number, number], p2: [number, number], t: number): [number, number] => [
    (1 - t) * (1 - t) * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
    (1 - t) * (1 - t) * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1],
  ];
  const dotPts = Array.from({ length: 13 }, (_, i) => q([150, 150], [400, -40], [650, 150], i / 12));
  const h = (width * 270) / 800;
  return (
    <svg viewBox="0 0 800 270" width={width} height={h} style={{ overflow: "visible", ...style }}>
      <path
        d="M 20 250 Q 400 40 780 250"
        fill="none"
        stroke={C.olive}
        strokeWidth={3}
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - draw}
        strokeLinecap="round"
      />
      {[
        [20, 250],
        [780, 250],
      ].map(([x, y], i) => (
        <rect
          key={i}
          x={x - 7}
          y={y - 7}
          width={14}
          height={14}
          fill={C.bgCenter}
          stroke={C.olive}
          strokeWidth={2}
          transform={`rotate(45 ${x} ${y})`}
          opacity={i === 0 ? (draw > 0.02 ? 1 : 0) : draw > 0.98 ? 1 : 0}
        />
      ))}
      {dotPts.map(([x, y], i) => (
        <circle
          key={i}
          cx={x}
          cy={y}
          r={i % 2 === 0 ? 3.2 : 2.2}
          fill={i % 2 === 0 ? C.olive : C.gold}
          opacity={(dots * 13 > i ? 1 : 0) * 0.9}
        />
      ))}
      <g transform={`translate(400 8) scale(${star})`} opacity={star * twinkle}>
        {Array.from({ length: 8 }, (_, i) => (
          <line
            key={i}
            x1={0}
            y1={0}
            x2={0}
            y2={-22}
            stroke={C.gold}
            strokeWidth={i % 2 === 0 ? 2.2 : 1.2}
            transform={`rotate(${i * 45})`}
            strokeLinecap="round"
          />
        ))}
        <circle r={3.5} fill={C.gold} />
      </g>
      <g transform={`translate(400 95) scale(${star})`} opacity={star}>
        <path
          d="M0 -20 C 2 -6, 6 -2, 20 0 C 6 2, 2 6, 0 20 C -2 6, -6 2, -20 0 C -6 -2, -2 -6, 0 -20 Z"
          fill={C.goldSoft}
          stroke={C.gold}
          strokeWidth={1}
        />
      </g>
    </svg>
  );
};

/** Thin divider with a sparkle in the middle. */
export const Divider: React.FC<{ from: number; width?: number }> = ({ from, width = 600 }) => {
  const C = useTheme();
  const frame = useCurrentFrame();
  const p = clamp(frame, from, from + 26, [0, 1], easeInOut);
  const half = width / 2;
  return (
    <svg width={width} height={44} viewBox={`0 0 ${width} 44`} style={{ overflow: "visible" }}>
      <line x1={half - 40} y1={22} x2={half - 40 - (half - 40) * p} y2={22} stroke={C.oliveSoft} strokeWidth={1.5} />
      <line x1={half + 40} y1={22} x2={half + 40 + (half - 40) * p} y2={22} stroke={C.oliveSoft} strokeWidth={1.5} />
      <g transform={`translate(${half} 22) scale(${p})`}>
        <path
          d="M0 -16 C 1.6 -5, 5 -1.6, 16 0 C 5 1.6, 1.6 5, 0 16 C -1.6 5, -5 1.6, -16 0 C -5 -1.6, -1.6 -5, 0 -16 Z"
          fill={C.goldSoft}
          stroke={C.gold}
          strokeWidth={1}
        />
      </g>
    </svg>
  );
};

/** Stamp chip (e.g. "ثقة جليل") that slams in like a seal. */
export const Stamp: React.FC<{ text: string; at: number; size?: number }> = ({ text, at, size = 28 }) => {
  const C = useTheme();
  const frame = useCurrentFrame();
  const p = clamp(frame, at, at + 12, [0, 1], pop);
  const o = clamp(frame, at, at + 4, [0, 1], Easing.linear);
  return (
    <div
      style={{
        opacity: o,
        scale: String(1.9 - 0.9 * p),
        rotate: `${-10 + 6 * p}deg`,
        fontFamily: F.sans,
        fontSize: size,
        fontWeight: 700,
        color: C.green,
        border: `2.5px solid ${C.green}`,
        background: C.chip,
        padding: "4px 18px",
        borderRadius: 10,
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </div>
  );
};

export const Txt: React.FC<{
  children: React.ReactNode;
  size: number;
  font?: "naskh" | "sans" | "noto";
  weight?: number;
  color?: string;
  lh?: number;
  align?: "center" | "right";
  style?: React.CSSProperties;
}> = ({ children, size, font = "naskh", weight = 400, color, lh = 1.65, align = "center", style }) => {
  const C = useTheme();
  return (
    <div
      lang="ar"
      dir="rtl"
      style={{
        fontFamily: font === "naskh" ? F.naskh : font === "noto" ? F.noto : F.sans,
        fontSize: size,
        fontWeight: weight,
        color: color ?? C.ink,
        lineHeight: lh,
        textAlign: align,
        fontFeatureSettings: '"kern", "liga", "calt", "mark", "mkmk"',
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/** Highlights one word inside a line (first occurrence). */
export const Highlight: React.FC<{ text: string; word?: string; color: string; underline?: number }> = ({
  text,
  word,
  color,
  underline = 0,
}) => {
  const C = useTheme();
  if (!word || !text.includes(word)) return <>{text}</>;
  const [a, ...rest] = text.split(word);
  const b = rest.join(word);
  return (
    <>
      {a}
      <span style={{ color, position: "relative", display: "inline-block" }}>
        {word}
        {underline > 0 ? (
          <span
            style={{
              position: "absolute",
              right: 0,
              bottom: -6,
              height: 5,
              width: `${underline * 100}%`,
              background: C.gold,
              borderRadius: 3,
            }}
          />
        ) : null}
      </span>
      {b}
    </>
  );
};
