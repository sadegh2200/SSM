import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame } from "remotion";
import { F, useTheme } from "../theme";
import type { Content, Plan, Point } from "../types";
import { Divider, Reveal, Scene, Txt, clamp } from "../ui";

type PPlan = NonNullable<Plan["scenes"]["points"]>;

const NUMERALS = ["١", "٢", "٣", "٤", "٥", "٦"];

const Tracker: React.FC<{ chips: string[]; active: number; done: boolean }> = ({ chips, active, done }) => {
  const C = useTheme();
  const frame = useCurrentFrame();
  const small = chips.length > 3;
  return (
    <div style={{ display: "flex", gap: small ? 12 : 18, direction: "rtl", flexWrap: "wrap", justifyContent: "center", maxWidth: 940 }}>
      {chips.map((c, i) => {
        const on = done || i <= active;
        const popS = i === active ? clamp(frame, 6, 22, [0.9, 1]) : 1;
        return (
          <div
            key={i}
            style={{
              fontFamily: F.sans,
              fontSize: small ? 26 : 30,
              fontWeight: 600,
              padding: small ? "8px 20px" : "10px 26px",
              borderRadius: 999,
              border: `1.5px solid ${on ? C.green : C.oliveSoft}`,
              color: on ? C.bgCenter : C.olive,
              background: on ? C.green : "transparent",
              scale: String(popS),
            }}
          >
            {c}
          </div>
        );
      })}
    </div>
  );
};

const Card: React.FC<{
  card: Point;
  index: number;
  count: number;
  length: number;
  chips: string[];
  titleSize: number;
  descSize: number;
}> = ({ card, index, count, length, chips, titleSize, descSize }) => {
  const C = useTheme();
  const frame = useCurrentFrame();
  const last = index === count - 1;
  const out = last ? 1 : clamp(frame, length - 10, length, [1, 0]);
  const ring = clamp(frame, 4, 34, [0, 1]);
  const R = 56;
  const circ = 2 * Math.PI * R;
  const quoteLines = card.quote ? (card.quote.lines ?? [card.quote.a, card.quote.b].filter(Boolean)) : [];
  const hasQuote = quoteLines.length > 0;
  return (
    <AbsoluteFill style={{ alignItems: "center", opacity: out }}>
      <div style={{ position: "absolute", top: hasQuote ? 500 : 520 }}>
        <Reveal from={0} duration={16} rise={10} scaleFrom={0.8}>
          <div style={{ position: "relative", width: 130, height: 130 }}>
            <svg width={130} height={130} style={{ position: "absolute", inset: 0 }}>
              <circle cx={65} cy={65} r={R} fill="none" stroke={C.goldSoft} strokeWidth={2} />
              <circle
                cx={65}
                cy={65}
                r={R}
                fill="none"
                stroke={C.green}
                strokeWidth={3}
                strokeDasharray={circ}
                strokeDashoffset={circ * (1 - ring)}
                strokeLinecap="round"
                transform="rotate(-90 65 65)"
              />
            </svg>
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: F.naskh,
                fontSize: 70,
                fontWeight: 700,
                color: C.green,
                paddingBottom: 8,
              }}
            >
              {NUMERALS[index] ?? String(index + 1)}
            </div>
          </div>
        </Reveal>
      </div>

      <div
        style={{
          position: "absolute",
          top: hasQuote ? 660 : 690,
          width: 900,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14,
        }}
      >
        {card.label ? (
          <Reveal from={8} duration={16} rise={14}>
            <Txt font="sans" size={34} weight={500} color={C.olive}>
              {card.label}
            </Txt>
          </Reveal>
        ) : null}
        <Reveal from={14} duration={20} rise={30}>
          <Txt size={titleSize} weight={700} color={C.green} lh={1.45}>
            {card.title}
          </Txt>
        </Reveal>
        {card.desc && card.desc.length ? (
          <Reveal from={34} duration={20} rise={22}>
            <Txt font="sans" size={descSize} weight={400} lh={1.75} style={{ maxWidth: 900 }}>
              {card.desc.map((d, i) => (
                <div key={i}>{d}</div>
              ))}
            </Txt>
          </Reveal>
        ) : null}
        {hasQuote ? (
          <Reveal from={60} duration={20} rise={22}>
            <div
              style={{
                marginTop: 16,
                padding: "20px 36px",
                borderRight: `4px solid ${C.gold}`,
                background: "rgba(255,255,255,0.35)",
                borderRadius: "4px 18px 18px 4px",
                display: "flex",
                flexDirection: "column",
                gap: 2,
                alignItems: "flex-start",
                maxWidth: 920,
              }}
            >
              {quoteLines.map((q, i) => (
                <Txt key={i} font="noto" size={44} color={i === quoteLines.length - 1 && quoteLines.length > 1 ? C.maroon : C.ink} align="right" lh={1.75}>
                  {q}
                </Txt>
              ))}
              {card.quote?.src ? (
                <Txt font="sans" size={28} color={C.olive} align="right" style={{ marginTop: 10 }}>
                  {card.quote.src}
                </Txt>
              ) : null}
            </div>
          </Reveal>
        ) : null}
      </div>

      <div style={{ position: "absolute", top: 1430, display: "flex", flexDirection: "column", alignItems: "center", gap: 22 }}>
        <Divider from={0} width={620} />
        <Tracker chips={chips} active={index} done={last && frame > length - 50} />
      </div>
    </AbsoluteFill>
  );
};

export const Points: React.FC<{ content: Content; plan: PPlan }> = ({ content, plan }) => {
  const cards = content.points ?? [];
  const chips = cards.map((c) => c.chip ?? c.title.split(" ")[0]);
  return (
    <Scene durationInFrames={plan.dur}>
      {cards.map((c, i) => (
        <Sequence key={i} from={plan.cards[i].from} durationInFrames={plan.cards[i].dur} layout="none">
          <Card
            card={c}
            index={i}
            count={cards.length}
            length={plan.cards[i].dur}
            chips={chips}
            titleSize={plan.title}
            descSize={plan.desc}
          />
        </Sequence>
      ))}
    </Scene>
  );
};
