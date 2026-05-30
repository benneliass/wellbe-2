# Packaging notes

The completed workbook and its build script were used as the source of truth. Workbook sheet data was reorganized into CSV tables and Markdown notes. Raw/source material was kept separate from extracted evidence by creating one source placeholder Markdown file per source under `01_sources/raw_sources/`.

Assumptions:
- `date_packaged` is `2026-05-30`.
- `research_topic` is consistent across structured rows.
- Author or organization was marked `unknown` unless it was already normalized in the completed workbook.
- Publication date and access date were not fully separable in some workbook rows; the original date string was preserved and access date was set to package date.
