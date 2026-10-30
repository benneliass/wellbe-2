/** Bundled Figtree advances at 1000px (ASCII 32–126), measured at weights 600/700.
 * Source: app/fonts/figtree-latin-wght-normal.woff2, SHA256 4ba7d3d096695818fe0686be4f1e82c6b05134e18a22260336130335027462dd.
 * Static metrics keep server and browser graph layouts identical before hydration. */
const SEMIBOLD = [241,307,376,630,558,802,646,227,370,370,485,629,245,411,232,415,645,419,571,551,628,578,574,548,613,574,282,287,629,629,629,509,991,699,612,723,695,590,550,750,750,282,537,644,530,853,774,783,594,785,637,610,572,705,711,975,653,630,635,336,415,336,569,436,247,524,592,544,591,551,384,596,565,250,282,517,236,864,564,581,597,586,363,466,393,564,542,815,512,556,483,391,257,391,628];
const BOLD = [238,312,412,631,554,813,647,245,382,382,488,632,257,408,248,432,648,422,579,556,633,581,580,556,612,580,301,305,632,632,632,513,992,714,612,725,700,589,554,743,750,289,552,666,537,857,773,787,603,789,645,607,584,704,722,985,679,647,632,344,432,344,581,434,263,533,596,546,595,554,393,601,570,262,291,538,246,872,568,581,601,592,379,466,402,568,556,835,536,576,477,394,256,394,667];

export function graphTextWidth(text: string, px: number, weight: number): number {
  const advances = weight >= 650 ? BOLD : SEMIBOLD;
  let units = 0;
  for (const character of text.normalize('NFD')) {
    if (/\p{Mark}/u.test(character) || character === '\u200d') continue;
    const code = character.codePointAt(0)!;
    units += code >= 32 && code <= 126 ? advances[code - 32]! : 1000;
  }
  // Allow for shaping, font-weight interpolation and fallback glyphs.
  return units / 1000 * px * 1.025 + 6;
}
