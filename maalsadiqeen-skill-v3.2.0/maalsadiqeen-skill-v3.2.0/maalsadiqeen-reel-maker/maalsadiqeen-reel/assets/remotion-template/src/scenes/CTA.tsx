import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { F, useTheme } from "../theme";
import type { Content, Plan } from "../types";
import { Divider, Reveal, Scene, Txt, clamp, pop } from "../ui";

const Icon: React.FC<{ kind: "send" | "save"; label: string; at: number }> = ({ kind, label, at }) => {
  const C = useTheme();
  const frame = useCurrentFrame();
  const p = clamp(frame, at, at + 16, [0, 1], pop);
  const pulse = 1 + 0.04 * Math.sin((frame - at) / 5) * (frame > at + 16 ? 1 : 0);
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, opacity: p, scale: String(p * pulse) }}>
      <div style={{ width: 96, height: 96, borderRadius: 28, border: `2px solid ${C.green}`, display: "flex", alignItems: "center", justifyContent: "center", background: C.chip }}>
        {kind === "send" ? (
          <svg width={48} height={48} viewBox="0 0 24 24" fill="none" stroke={C.green} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 2L11 13" />
            <path d="M22 2L15 22l-4-9-9-4 20-7z" />
          </svg>
        ) : (
          <svg width={48} height={48} viewBox="0 0 24 24" fill="none" stroke={C.green} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
          </svg>
        )}
      </div>
      <div style={{ fontFamily: F.sans, fontSize: 30, fontWeight: 600, color: C.inkSoft }}>{label}</div>
    </div>
  );
};

/** Joins sources into at most two balanced lines separated by bullets. */
const sourceLines = (src: string[]): string[] => {
  if (src.length <= 2) return [src.join("  •  ")];
  const half = Math.ceil(src.length / 2);
  return [src.slice(0, half).join("  •  "), src.slice(half).join("  •  ")];
};

export const CTA: React.FC<{ content: Content; plan: NonNullable<Plan["scenes"]["cta"]> }> = ({ content, plan }) => {
  const C = useTheme();
  const cta = content.cta ?? {};
  const sources = content.sources ?? [];
  const icons = cta.icons !== false;
  return (
    <Scene durationInFrames={plan.dur} fadeOut={34}>
      <AbsoluteFill style={{ alignItems: "center" }}>
        {sources.length ? (
          <div style={{ position: "absolute", top: 380, width: 940, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
            <Reveal from={0} duration={16} rise={12}>
              {sourceLines(sources).map((l, i) => (
                <Txt key={i} font="sans" size={30} weight={500} color={C.olive} lh={1.8}>
                  {l}
                </Txt>
              ))}
            </Reveal>
          </div>
        ) : null}

        <div style={{ position: "absolute", top: 700, width: 960, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
          {cta.line1 ? (
            <Reveal from={30} duration={22} rise={30} scaleFrom={1.04}>
              <Txt size={cta.line1.length > 22 ? 84 : 104} weight={700} color={C.green} lh={1.45}>
                {cta.line1}
              </Txt>
            </Reveal>
          ) : null}
          {cta.line2 ? (
            <Reveal from={50} duration={20} rise={24}>
              <Txt size={64} lh={1.6}>
                {cta.line2}
              </Txt>
            </Reveal>
          ) : null}
          <div style={{ marginTop: 40 }}>
            <Divider from={62} width={560} />
          </div>
          {icons ? (
            <div style={{ marginTop: 34, display: "flex", gap: 90, direction: "rtl" }}>
              <Icon kind="send" label="شارِك" at={78} />
              <Icon kind="save" label="احفَظ" at={88} />
            </div>
          ) : null}
        </div>

        {cta.footer ? (
          <div style={{ position: "absolute", top: 1400 }}>
            <Reveal from={100} duration={18} rise={14}>
              <Txt font="sans" size={32} weight={500} color={C.inkSoft}>
                {cta.footer}
              </Txt>
            </Reveal>
          </div>
        ) : null}
      </AbsoluteFill>
    </Scene>
  );
};
