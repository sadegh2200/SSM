import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

// Local fonts (bundled in public/fonts). Each loadFont() delays rendering until the font is ready.
export const fontsReady = Promise.all([
  loadFont({ family: "Amiri", url: staticFile("fonts/Amiri-Regular.ttf"), weight: "400" }),
  loadFont({ family: "Amiri", url: staticFile("fonts/Amiri-Bold.ttf"), weight: "700" }),
  loadFont({ family: "Vazirmatn", url: staticFile("fonts/Vazirmatn.ttf"), weight: "100 900" }),
  loadFont({ family: "Noto Naskh Arabic", url: staticFile("fonts/NotoNaskhArabic.ttf"), weight: "400 700" }),
]);
