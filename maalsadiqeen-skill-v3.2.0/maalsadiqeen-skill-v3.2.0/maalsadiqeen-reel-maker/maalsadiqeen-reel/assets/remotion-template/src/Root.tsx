import React from "react";
import { CalculateMetadataFunction, Composition, staticFile } from "remotion";
import { Reel } from "./Reel";
import type { ReelProps } from "./types";
import { H, W } from "./theme";

// Duration and fps come from plan.json (written by scripts/plan.py); content from content.json.
const calculateMetadata: CalculateMetadataFunction<ReelProps> = async () => {
  const [content, plan] = await Promise.all([
    fetch(staticFile("content.json")).then((r) => r.json()),
    fetch(staticFile("plan.json")).then((r) => r.json()),
  ]);
  return { durationInFrames: plan.total, fps: plan.fps, props: { content, plan } };
};

const placeholder: ReelProps = {
  content: { hook: { line1: "" }, hadith: { lines: [] } },
  plan: { fps: 30, total: 30, order: [], scenes: {}, sfx: [] },
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Reel"
    component={Reel}
    durationInFrames={30}
    fps={30}
    width={W}
    height={H}
    defaultProps={placeholder}
    calculateMetadata={calculateMetadata}
  />
);
