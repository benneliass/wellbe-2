# Packaging notes

Files were organized into the requested evidence archive structure. Structured evidence was exported to CSV. Readable summaries and analysis were exported to Markdown.

Cleanup performed:

- Normalized source IDs.
- Added `research_topic` and `date_packaged` to structured CSV rows.
- Kept quotes short.
- Added `unknown` where metadata was not available from the completed research.
- Created source-summary Markdown files instead of saving raw webpages.

Assumptions:

- `access_date` is the packaging date unless the completed research stated a different date.
- Evidence quality follows the completed research definitions.
- Public patient-review and advocacy sources are treated as reported experience, not independently verified clinical fact.
