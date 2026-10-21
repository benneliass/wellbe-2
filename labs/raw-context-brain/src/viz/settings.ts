// One place for the picture. The numbers are the current look.
// A later caller can pass a different copy. The layout math stays the same.

export const mapSettings = {
  circle: {
    base: 36,
    perLink: 8,
  },
  keyword: {
    fittedLetters: 6,
    fillOfDiameter: 0.78,
    charWidthRatio: 0.56,
    minDiameter: 8,
    fallbackPx: 11,
  },
  headline: {
    asideLimit: 48,
    colonWindow: 48,
    clipBreakAfter: 16,
  },
  curve: {
    weight: 0.42,
    control: 0.07,
  },
  turn: 2.399963,
  /** A note on a link counts only along the middle of that link. */
  linkBand: {
    start: 0.12,
    end: 0.88,
  },
  clearance: {
    pointCap: 64,
    fallbackSize: 12,
    spreadPad: 4,
    linkPad: 10,
    contentFraction: 0.6,
    minContent: 120,
    fallbackWidth: 900,
    fallbackHeight: 700,
    fittedFraction: 0.1,
  },
  copy: {
    emptyMap: "Click a note on the map.",
  },
} as const;

export type MapSettings = typeof mapSettings;
