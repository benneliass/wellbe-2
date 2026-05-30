# Evidence quality, limitations, and gaps

## Package ingestion status

All five attached `.tar.gz` evidence packages extracted successfully. I inspected manifests, source databases, extracted evidence tables, analysis files, implications, reports, and available workbook structures. The packages use slightly different internal structures, but each includes source logs and extracted evidence tables. The original `.xlsx` files were inspected at workbook/sheet level; their main row-level contents are also represented in CSV/Markdown outputs in the packages.

## Primary limitations inherited from the packages

- The packages generally do not include downloaded raw webpages/PDFs/screenshots; they include source-summary Markdown stubs and source URLs.
- Several sources have unknown or approximate publication dates, authors, or detailed metadata.
- Patient reviews, advocacy stories, and public quotes are valuable workflow evidence but are not prevalence estimates and are often not independently clinically adjudicated.
- Some Research B case rows preserve case IDs but have `source_id = unknown`; the original workbook and source log retain URLs for many cases, but the normalized case CSV does not always carry source IDs.
- Counts in package metrics are curated evidence-library counts, not epidemiologic rates, unless the source row explicitly describes a population metric.
- The synthesis did not add a new live web search; it translates the attached packages only.

## Product evidence gaps

- Prospective workflow testing is needed to measure whether features reduce missed follow-up, repeated-visit diagnostic delay, and patient distrust without increasing alert fatigue.
- Region-specific adaptations need local governance, especially for language/cultural safety, CHW workflows, and low-resource diagnostic availability.
- Bias guardrails need safety evaluation to avoid stigmatizing mental-health conditions or clinicians while still catching diagnostic overshadowing.
- Patient-facing uncertainty language needs usability testing across literacy, language, age, disability, and cultural contexts.
