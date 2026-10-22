import React from "react";
import { AbsoluteFill, Easing, useCurrentFrame } from "remotion";
import { useTheme } from "../theme";
import type { Content, Plan } from "../types";
import { Reveal, Scene, Stamp, Txt, clamp, ease, pop } from "../ui";

type SPlan = NonNullable<Plan["scenes"]["sanad"]>;

const TOP = 500;
const LINE_X = 790;

export const Sanad: React.FC<{ content: Content; plan: SPlan }> = ({ content, plan }) => {
  const C = useTheme();
  const frame = useCurrentFrame();
  const s = content.sanad!;
  const chain = s.chain ?? [];
  const ROW = plan.row;
  const START = plan.start;
  const STEP = plan.step;
  const SEAL = plan.seal_at;
  const lastNode = START + STEP * Math.max(chain.length - 1, 0);
  const lineLen = clamp(frame, START, lastNode + 10, [0, ROW * Math.max(chain.length - 1, 0)], Easing.linear);
  const recede = clamp(frame, SEAL - 6, SEAL + 16, [0, 1]);
  const sealP = clamp(frame, SEAL, SEAL + 16, [0, 1], pop);
  const sealO = clamp(frame, SEAL, SEAL + 5, [0, 1], Easing.linear);
  const flash = clamp(frame, SEAL + 2, SEAL + 18, [0.35, 0], Easing.linear);
  const hasChain = chain.length > 0;

  return (
    <Scene durationInFrames={plan.dur}>
      <AbsoluteFill style={{ alignItems: "center" }}>
        <div style={{ position: "absolute", top: 330, display: "flex", flexDirection: "column", alignItems: "center", gap: 2, opacity: 1 - recede * 0.75 }}>
          {s.question ? (
            <Reveal from={0} duration={18} rise={16}>
              <Txt size={80} weight={700} lh={1.4}>
                {s.question}
              </Txt>
            </Reveal>
          ) : null}
          {s.sub ? (
            <Reveal from={12} duration={16} rise={12}>
              <Txt font="sans" size={34} weight={500} color={C.olive}>
                {s.sub}
              </Txt>
            </Reveal>
          ) : null}
        </div>

        {hasChain ? (
          <div
            style={{
              position: "absolute",
              top: TOP,
              width: 820,
              height: ROW * chain.length,
              opacity: 1 - recede * 0.82,
              scale: String(1 - recede * 0.06),
              filter: `blur(${recede * 3}px)`,
            }}
          >
            <svg width={820} height={ROW * chain.length} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
              <line x1={LINE_X} y1={ROW / 2} x2={LINE_X} y2={ROW / 2 + lineLen} stroke={C.olive} strokeWidth={2.5} />
            </svg>
            {chain.map((n, i) => {
              const at = START + STEP * i;
              const p = clamp(frame, at, at + 16, [0, 1]);
              return (
                <div key={i} style={{ position: "absolute", top: i * ROW, left: 0, width: 820, height: ROW, direction: "rtl" }}>
                  <div style={{ position: "absolute", left: LINE_X - 15, top: ROW / 2 - 15, width: 30, height: 30, scale: String(p) }}>
                    {n.imam ? (
                      <svg width={30} height={30} viewBox="-15 -15 30 30">
                        {Array.from({ length: 8 }, (_, k) => (
                          <line key={k} x1={0} y1={0} x2={0} y2={-14} stroke={C.gold} strokeWidth={k % 2 ? 1.2 : 2.2} transform={`rotate(${k * 45})`} strokeLinecap="round" />
                        ))}
                        <circle r={4} fill={C.green} />
                      </svg>
                    ) : (
                      <svg width={30} height={30} viewBox="-15 -15 30 30">
                        <circle r={9} fill={C.bgCenter} stroke={C.green} strokeWidth={2.5} />
                        <circle r={3.5} fill={C.green} />
                      </svg>
                    )}
                  </div>
                  <div
                    style={{
                      position: "absolute",
                      right: 820 - LINE_X + 34,
                      top: 0,
                      height: ROW,
                      display: "flex",
                      alignItems: "center",
                      opacity: p,
                      translate: `${(1 - p) * 24}px 0`,
                    }}
                  >
                    <Txt
                      font={n.imam ? "naskh" : "sans"}
                      size={n.imam ? plan.name + 12 : plan.name}
                      weight={n.imam ? 700 : 500}
                      color={n.imam ? C.green : C.ink}
                      align="right"
                      lh={1.3}
                    >
                      {n.name}
                    </Txt>
                  </div>
                  {n.grade ? (
                    <div style={{ position: "absolute", left: 20, top: ROW / 2 - 24, height: 48, display: "flex", alignItems: "center" }}>
                      <Stamp text={n.grade} at={at + 10} size={plan.chip} />
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : null}

        {s.verdict ? (
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", pointerEvents: "none" }}>
            <AbsoluteFill style={{ background: C.bgCenter, opacity: flash }} />
            <div
              style={{
                opacity: sealO,
                scale: String(1.6 - 0.6 * sealP),
                rotate: `${-7 + 3 * sealP}deg`,
                translate: "0px 40px",
                padding: 10,
                border: `3px solid ${C.green}`,
                borderRadius: 26,
              }}
            >
              <div
                style={{
                  border: `1.5px solid ${C.green}`,
                  borderRadius: 18,
                  padding: "26px 64px 30px",
                  background: "rgba(252,247,241,0.92)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                <Txt size={s.verdict.length > 20 ? 74 : 92} weight={700} color={C.green} lh={1.35}>
                  {s.verdict}
                </Txt>
                {s.verdict_sub ? (
                  <Txt font="sans" size={34} weight={500} color={C.inkSoft}>
                    {s.verdict_sub}
                  </Txt>
                ) : null}
              </div>
            </div>
            {s.note ? (
              <div
                style={{
                  position: "absolute",
                  top: 1340,
                  width: 900,
                  opacity: clamp(frame, SEAL + 22, SEAL + 40, [0, 1], ease),
                  translate: `0px ${clamp(frame, SEAL + 22, SEAL + 40, [16, 0])}px`,
                }}
              >
                <Txt font="sans" size={30} color={C.olive} lh={1.7}>
                  {s.note}
                </Txt>
              </div>
            ) : null}
          </AbsoluteFill>
        ) : null}
      </AbsoluteFill>
    </Scene>
  );
};
