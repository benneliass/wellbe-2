# Packaging notes

Files were organized according to the requested archive structure. Structured CSVs include `research_topic` and `date_packaged` fields. Empty folders include `.keep` files.

Cleanup performed:

- Converted the completed research answer into structured source, fact, metric, quote, case/example, and evidence tables.
- Created source-summary stubs for raw source folders where full source files were not saved.
- Kept facts, quotes, examples, analysis, and implications in separate files.

Assumptions:

- `access_date` is set to the packaging date because the package is based on the completed research state.
- Unknown publication dates are marked `unknown`.
- Quote snippets are short and should be verified against the source before republication.
