import React from "react";
import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { Audio } from "@remotion/media";
import { ThemeProvider } from "./theme";
import type { ReelProps } from "./types";
import { BrandFrame, Paper } from "./ui";
import { Hook } from "./scenes/Hook";
import { Hadith } from "./scenes/Hadith";
import { Points } from "./scenes/Points";
import { Bayan } from "./scenes/Bayan";
import { Sanad } from "./scenes/Sanad";
import { CTA } from "./scenes/CTA";
import "./fonts";

export const Reel: React.FC<ReelProps> = ({ content, plan }) => {
  const s = plan.scenes;
  const audio = content.audio ?? {};
  const bed = audio.bed !== false;
  const sfx = audio.sfx !== false;
  return (
    <ThemeProvider palette={content.brand?.palette}>
      <AbsoluteFill lang="ar" dir="rtl">
        <Paper />

        {s.hook ? (
          <Sequence from={s.hook.from} durationInFrames={s.hook.dur} layout="none">
            <Hook content={content} plan={s.hook} />
          </Sequence>
        ) : null}
        {s.hadith ? (
          <Sequence from={s.hadith.from} durationInFrames={s.hadith.dur} layout="none">
            <Hadith content={content} plan={s.hadith} />
          </Sequence>
        ) : null}
        {s.points && content.points?.length ? (
          <Sequence from={s.points.from} durationInFrames={s.points.dur} layout="none">
            <Points content={content} plan={s.points} />
          </Sequence>
        ) : null}
        {s.bayan && content.bayan ? (
          <Sequence from={s.bayan.from} durationInFrames={s.bayan.dur} layout="none">
            <Bayan content={content} plan={s.bayan} />
          </Sequence>
        ) : null}
        {s.sanad && content.sanad ? (
          <Sequence from={s.sanad.from} durationInFrames={s.sanad.dur} layout="none">
            <Sanad content={content} plan={s.sanad} />
          </Sequence>
        ) : null}
        {s.cta ? (
          <Sequence from={s.cta.from} durationInFrames={s.cta.dur} layout="none">
            <CTA content={content} plan={s.cta} />
          </Sequence>
        ) : null}

        <BrandFrame logo={content.brand?.logo} branch={content.brand?.branch} handle={content.brand?.handle} total={plan.total} />

        {bed ? <Audio src={staticFile("audio/pad.wav")} volume={audio.bed_volume ?? 0.9} /> : null}
        {sfx
          ? plan.sfx.map((x, i) => (
              <Sequence key={i} from={x.at} layout="none">
                <Audio src={staticFile(`audio/${x.src}.wav`)} volume={x.vol} />
              </Sequence>
            ))
          : null}
      </AbsoluteFill>
    </ThemeProvider>
  );
};
