/** The reference pebble fits inside the layout's circular safety envelope. */
export const PEBBLE_OUTLINE = "M -9 -97 C 29 -101 65 -78 83 -43 C 103 -7 99 35 72 65 C 45 96 1 100 -35 87 C -73 74 -96 42 -96 7 C -98 -30 -76 -61 -49 -81 C -35 -91 -22 -96 -9 -97 Z";

/** Resolve colors without a browser, keeping server and client paint identical. */
function colorChannels(hex: string): [number, number, number] {
  const value = hex.replace(/^#/, '');
  if (!/^(?:[a-f\d]{3}|[a-f\d]{6})$/i.test(value)) throw new Error('Map material colors must be three- or six-digit hex colors');
  const full = value.length === 3 ? [...value].map((channel) => channel + channel).join('') : value;
  return [0, 2, 4].map((index) => parseInt(full.slice(index, index + 2), 16)) as [number, number, number];
}

export function pebblePalette(hex: string) {
  const channels = colorChannels(hex).map((channel) => channel / 255);
  const [r, g, b] = channels as [number, number, number];
  const high = Math.max(r, g, b), low = Math.min(r, g, b), delta = high - low;
  const hue = !delta ? 215 : high === r ? ((g - b) / delta + (g < b ? 6 : 0)) * 60 : high === g ? ((b - r) / delta + 2) * 60 : ((r - g) / delta + 4) * 60;
  const saturation = delta < 0.18 ? 7 : hue > 245 && hue < 300 ? 35 : hue > 195 && hue < 245 ? 35 : 31;
  const tone = (s: number, l: number) => `hsl(${hue.toFixed(1)} ${s}% ${l}%)`;
  return {
    light: tone(saturation * 0.7, 96),
    crown: tone(saturation, 89),
    body: tone(saturation, hue > 165 && hue < 195 ? 79 : 84),
    base: tone(saturation * 0.85, 75),
    ink: tone(Math.min(45, saturation * 1.4), 32),
  };
}

export function porcelainTint(hex: string, white = 0.7): string {
  const blend = Math.max(0, Math.min(1, white));
  return `#${colorChannels(hex).map((channel) => Math.round(channel * (1 - blend) + 255 * blend).toString(16).padStart(2, "0")).join("")}`;
}
