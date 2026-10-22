# content.json schema

All text is formal Arabic. Optional blocks are omitted (not `null`) when the cards do not contain them.
Paths in `brand` are relative to the studio `public/` folder.

```jsonc
{
  "slug": "shiatuna-almuslimun-liamrina",      // ASCII, used for file names
  "title": "شيعتنا المسلمون لأمرنا",            // human title (post.md heading)
  "brand": {
    "handle": "@maalsadiqeen",                 // fallback when logo is missing
    "logo": "img/logo.png",                    // optional, keyed PNG (bottom-left corner of the frame)
    "branch": "img/branch.png",                // optional ornament (top-right)
    "palette": { "green": "rgb(10,79,6)" }     // optional overrides of DEFAULT_PALETTE (any key)
  },
  "hook": {
    "line1": "هل يكفي الحُبُّ",                  // required, 3–7 words
    "line2": "لتكونَ من شيعتِهم؟",               // optional second line
    "highlight": "الحُبُّ",                       // word painted green + underlined (must appear in line1/line2)
    "sub": "الإمامُ الرضا عليه السلام يُجيب"       // small olive line under the hook
  },
  "hadith": {
    "intro": "قالَ الإمامُ الرضا عليه السلام:",   // optional
    "lines": [                                   // 1–10 lines, ≤ 6 words each, fully vocalized
      { "t": "شيعتُنا المُسلِّمونَ لأمرِنا،", "style": "lead" },
      { "t": "الآخِذونَ بقولِنا،" },                    // style defaults to "body"
      { "t": "فمَن لم يكُن كذلكَ فليسَ منّا.", "style": "warning" }
    ],
    "bridge": "ثلاثُ صفاتٍ… لا واحدة",           // optional thesis line shown after the hadith
    "continued": "تتمّةُ الحديث"                  // optional label for page 2+ (default shown)
  },
  "points": [                                    // optional, 2–5 cards
    {
      "chip": "التسليم",                          // 1–2 words for the progress tracker
      "label": "الصفةُ الأولى",                   // small line above the title
      "title": "المُسلِّمونَ لأمرِنا",              // required — the hadith's own words
      "desc": ["…", "…"],                         // ≤ 2–3 short lines, card wording only
      "quote": { "lines": ["«…»", "«…»"], "src": "الإمامُ الباقر عليه السلام — الوافي ج٣ ص٩١١" }  // optional supporting narration
    }
  ],
  "bayan": {                                     // optional explanation scene (use instead of points for 3-card posts)
    "title": "بيانُ المعنى",
    "lines": ["…", "…", "…"],                     // ≤ 6 lines
    "emphasis": [2],                              // indices rendered maroon/bold
    "src": "مرآة العقول ج٤ ص٢٠٥"
  },
  "sanad": {                                     // optional; verdict required when chain is present
    "question": "هل الحديثُ صحيح؟",
    "sub": "تحقيقُ سلسلةِ السَّند",
    "chain": [                                   // author → … → Imam, ≤ 12 nodes
      { "name": "الشيخُ الصدوق", "grade": "ثقة" },
      { "name": "الإمامُ الرضا عليه السلام", "imam": true }
    ],
    "verdict": "السَّنَدُ صحيحٌ معتبَرٌ",
    "verdict_sub": "جميعُ رجالِه ثِقات",
    "note": "رواه الشيخُ الصدوق في صفاتِ الشيعة…"   // small line under the seal
  },
  "sources": ["وسائل الشيعة ج٢٧ ص١١٦", "صفات الشيعة ص٣"],   // ≤ 4–6, Arabic digits
  "cta": {
    "line1": "أرسِلْها لمن يُحبُّهم…",            // share-oriented
    "line2": "ليعرفَ كيفَ يكونُ منهم",
    "icons": true,                                // send + save icons
    "footer": "احفظِ المقطعَ لتعودَ إلى السَّند"
  },
  "audio": { "bed": true, "bed_volume": 0.9, "sfx": true }
}
```

# plan.json (generated — do not hand-write)

```jsonc
{
  "fps": 30, "total": 1390, "pace": 0.756, "order": ["hook","hadith","points","sanad","cta"],
  "scenes": {
    "hook":   { "from": 0, "dur": 105, "size": 94, "sub_at": 38 },
    "hadith": { "from": 100, "dur": 345, "body": 78, "lead": 128, "warning": 66, "intro": 44,
                "pages": [ { "from": 0, "dur": 345, "top": 638, "intro_at": 22, "lines": [ { "i": 0, "at": 64 } ], "bridge_at": 279 } ] },
    "points": { "from": 440, "dur": 531, "title": 94, "desc": 44, "cards": [ { "from": 0, "dur": 177 } ] },
    "bayan":  { "from": 0, "dur": 300, "size": 44, "top": 655, "lines_at": [24, 90, 160] },
    "sanad":  { "from": 966, "dur": 309, "start": 30, "step": 26, "seal_at": 210, "row": 112, "name": 40, "chip": 28 },
    "cta":    { "from": 1270, "dur": 120 }
  },
  "sfx": [ { "at": 0, "src": "boom", "vol": 0.7 } ]        // src = file name in public/audio without .wav
}
```

Frames inside a scene are relative to the scene's `from`; frames inside a hadith page are relative to the page.
Scenes overlap by 5 frames (crossfade). `total` drives `durationInFrames` through `calculateMetadata`.
