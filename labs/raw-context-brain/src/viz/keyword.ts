const SKIP = new Set([
  "a", "an", "the", "and", "or", "of", "with", "to", "for", "in", "on", "at", "from", "by", "as",
  "into", "over", "after", "before", "despite", "than", "more", "most", "many", "very", "began",
  "begin", "beginning", "showed", "shown", "described", "present", "since", "during", "without",
  "within", "not", "no", "its", "their", "this", "that", "were", "was", "are", "is", "been",
  "had", "have", "has",
]);

const WEAK = new Set([
  "loose", "recurrent", "marked", "additional", "longstanding", "high", "multiple", "negative",
  "elevated", "repeated", "persistent", "persisted", "unintentional", "exact", "value", "associated",
]);

const MAX = 14;

/** A short word from the note's own text, short enough to sit beside the circle. */
export function memoryKeyword(text: string): string {
  const line = text.split("\n")[0]?.trim() ?? "";
  if (!line) return "";
  const colon = line.indexOf(":");
  const head = colon > 0 && colon <= 28 ? line.slice(0, colon).trim() : line;
  const words = head
    .replace(/[;,./()]/g, " ")
    .split(/[\s/]+/)
    .map((word) => word.trim())
    .filter((word) => word.length > 1);
  const specific = words.filter((word) => {
    const lower = word.toLowerCase();
    return !SKIP.has(lower) && !WEAK.has(lower) && word.length <= MAX;
  });
  const pick = specific[0] ?? words.find((word) => word.length <= MAX) ?? "";
  return present(pick);
}

function present(word: string): string {
  if (!word) return "";
  if (word.length <= 6 && word === word.toUpperCase()) return word;
  if (/[A-Z]/.test(word.slice(1))) return word;
  return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
}
