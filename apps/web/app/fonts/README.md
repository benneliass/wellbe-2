# Self-hosted fonts

Loaded by `app/layout.tsx` through `next/font/local`, so builds (including the
Docker image build) never download from Google Fonts.

| File | Family | Axis | Source | Licence |
|---|---|---|---|---|
| `figtree-latin-wght-normal.woff2` | Figtree | wght 300–900 | `@fontsource-variable/figtree@5.3.0` | `OFL-Figtree.txt` |
| `noto-sans-latin-wght-normal.woff2` | Noto Sans | wght 100–900 | `@fontsource-variable/noto-sans@5.3.0` | `OFL-NotoSans.txt` |
| `jetbrains-mono-latin-wght-normal.woff2` | JetBrains Mono | wght 100–800 | `@fontsource-variable/jetbrains-mono@5.3.0` | `OFL-JetBrainsMono.txt` |

All three are the latin subset (same unicode range Google Fonts serves for
`subsets: ["latin"]`) and are licensed under the SIL Open Font License 1.1.

To update: `npm pack @fontsource-variable/<family>`, copy
`package/files/<family>-latin-wght-normal.woff2` and `package/LICENSE` here.
