import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame } from "remotion";
import { useTheme } from "../theme";
import type { Content, HadithPage, Plan } from "../types";
import { ArcOrnament, Divider, Reveal, Scene, Txt, clamp } from "../ui";

type HPlan = NonNullable<Plan["scenes"]["hadith"]>;

const Page: React.FC<{ content: Content; plan: HPlan; page: HadithPage; pageIndex: number; pageCount: number }> = ({
  content,
  plan,
  page,
  pageIndex,
  pageCount,
}) => {
  const C = useTheme();
  const frame = useCurrentFrame();
  const out = pageIndex < pageCount - 1 ? clamp(frame, page.dur - 12, page.dur, [1, 0]) : 1;
  const lines = page.lines.map((l) => ({ ...content.hadith.lines[l.i], at: l.at }));
  const warningIdx = lines.findIndex((l) => l.style === "warning");
  const rule = warningIdx >= 0 ? clamp(frame, lines[warningIdx].at + 8, lines[warningIdx].at + 32, [0, 1]) : 0;
  return (
    <AbsoluteFill style={{ alignItems: "center", opacity: out }}>
      <div style={{ position: "absolute", top: 350 }}>
        <ArcOrnament from={pageIndex === 0 ? 0 : -60} width={840} />
      </div>
      <div
        style={{
          position: "absolute",
          top: page.top ?? 632,
          width: 940,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 2,
        }}
      >
        {content.hadith.intro && pageIndex === 0 ? (
          <Reveal from={page.intro_at} duration={18} rise={14}>
            <Txt font="noto" size={plan.intro} color={C.green} lh={1.8}>
              {content.hadith.intro}
            </Txt>
          </Reveal>
        ) : null}
        {pageIndex > 0 ? (
          <Reveal from={0} duration={14} rise={8}>
            <Txt font="sans" size={30} weight={500} color={C.olive} style={{ marginBottom: 10 }}>
              {content.hadith.continued ?? "تتمّةُ الحديث"}
            </Txt>
          </Reveal>
        ) : null}
        {lines.map((l, k) => {
          const isLead = l.style === "lead";
          const isWarn = l.style === "warning";
          const size = isLead ? plan.lead : isWarn ? plan.warning : plan.body;
          return (
            <Reveal key={k} from={l.at} duration={isWarn ? 20 : 18} rise={26}>
              <div style={{ position: "relative", padding: isWarn ? "0 10px" : 0 }}>
                <Txt
                  font="noto"
                  size={size}
                  color={isLead ? C.green : isWarn ? C.maroon : C.ink}
                  weight={isLead || isWarn ? 700 : 500}
                  lh={isLead ? 1.5 : isWarn ? 1.8 : 1.75}
                >
                  {l.t}
                </Txt>
                {isWarn ? (
                  <div
                    style={{
                      position: "absolute",
                      bottom: 10,
                      right: "50%",
                      translate: "50% 0",
                      height: 3,
                      width: `${rule * 92}%`,
                      background: C.maroon,
                      opacity: 0.55,
                      borderRadius: 2,
                    }}
                  />
                ) : null}
              </div>
            </Reveal>
          );
        })}
      </div>
      {page.bridge_at !== undefined && content.hadith.bridge ? (
        <div style={{ position: "absolute", top: 1420, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
          <Divider from={page.bridge_at - 16} width={620} />
          <Reveal from={page.bridge_at} duration={18} rise={16}>
            <Txt font="sans" size={42} weight={600} color={C.inkSoft}>
              {content.hadith.bridge}
            </Txt>
          </Reveal>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const Hadith: React.FC<{ content: Content; plan: HPlan }> = ({ content, plan }) => (
  <Scene durationInFrames={plan.dur}>
    {plan.pages.map((p, i) => (
      <Sequence key={i} from={p.from} durationInFrames={p.dur} layout="none">
        <Page content={content} plan={plan} page={p} pageIndex={i} pageCount={plan.pages.length} />
      </Sequence>
    ))}
  </Scene>
);
