import React from "react";
import { AbsoluteFill } from "remotion";
import { useTheme } from "../theme";
import type { Content, Plan } from "../types";
import { Divider, Reveal, Scene, Txt } from "../ui";

type BPlan = NonNullable<Plan["scenes"]["bayan"]>;

/** Explanation scene: one supporting narration / tafsir shown as a dignified quote block. */
export const Bayan: React.FC<{ content: Content; plan: BPlan }> = ({ content, plan }) => {
  const C = useTheme();
  const b = content.bayan!;
  const emphasis = new Set(b.emphasis ?? []);
  return (
    <Scene durationInFrames={plan.dur}>
      <AbsoluteFill style={{ alignItems: "center" }}>
        <div style={{ position: "absolute", top: (plan.top ?? 620) - 220, width: 940, display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          {b.title ? (
            <Reveal from={0} duration={18} rise={16}>
              <Txt size={64} weight={700} lh={1.45}>
                {b.title}
              </Txt>
            </Reveal>
          ) : null}
          <div style={{ marginTop: 6 }}>
            <Divider from={10} width={520} />
          </div>
        </div>
        <div
          style={{
            position: "absolute",
            top: plan.top ?? 620,
            width: 920,
            padding: "34px 44px",
            borderRight: `4px solid ${C.gold}`,
            background: "rgba(255,255,255,0.35)",
            borderRadius: "4px 22px 22px 4px",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {b.lines.map((l, i) => (
            <Reveal key={i} from={plan.lines_at[i] ?? 20 + i * 30} duration={18} rise={18}>
              <Txt font="noto" size={plan.size} color={emphasis.has(i) ? C.maroon : C.ink} weight={emphasis.has(i) ? 700 : 500} align="right" lh={1.8}>
                {l}
              </Txt>
            </Reveal>
          ))}
          {b.src ? (
            <Reveal from={(plan.lines_at[b.lines.length - 1] ?? 60) + 20} duration={16} rise={12}>
              <Txt font="sans" size={28} color={C.olive} align="right" style={{ marginTop: 14 }}>
                {b.src}
              </Txt>
            </Reveal>
          ) : null}
        </div>
      </AbsoluteFill>
    </Scene>
  );
};
