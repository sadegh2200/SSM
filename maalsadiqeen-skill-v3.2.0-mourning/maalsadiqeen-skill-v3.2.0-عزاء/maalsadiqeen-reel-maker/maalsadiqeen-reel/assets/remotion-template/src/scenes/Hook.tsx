import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { useTheme } from "../theme";
import type { Content, Plan } from "../types";
import { Highlight, Reveal, Scene, Txt, clamp } from "../ui";

export const Hook: React.FC<{ content: Content; plan: NonNullable<Plan["scenes"]["hook"]> }> = ({
  content,
  plan,
}) => {
  const C = useTheme();
  const frame = useCurrentFrame();
  const underline = clamp(frame, 22, 44, [0, 1]);
  const { line1, line2, highlight, sub } = content.hook;
  return (
    <Scene durationInFrames={plan.dur} fadeIn={0} fadeOut={10}>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: "0 70px", gap: 26 }}>
        <Reveal from={2} duration={20} scaleFrom={1.07} rise={10}>
          <Txt size={plan.size} weight={700} lh={1.5}>
            <Highlight text={line1} word={highlight} color={C.green} underline={underline} />
          </Txt>
          {line2 ? (
            <Txt size={plan.size} weight={700} lh={1.5}>
              <Highlight text={line2} word={line1.includes(highlight ?? "\u0000") ? undefined : highlight} color={C.green} underline={underline} />
            </Txt>
          ) : null}
        </Reveal>
        {sub ? (
          <Reveal from={plan.sub_at} duration={18} rise={18}>
            <Txt font="sans" size={38} weight={500} color={C.olive} lh={1.6}>
              {sub}
            </Txt>
          </Reveal>
        ) : null}
      </AbsoluteFill>
    </Scene>
  );
};
