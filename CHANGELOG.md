# Changelog

## v0.3.0 — Commercial Performance & Targets (2026-11-26)

- Added the locally executed performance and targets module; reused the corrected profitability module for read-only access and sales preparation.
- Integrated sales, traffic and targets with pre-aggregation, checked joins, date and cardinality rules, and reconciliation.
- Added weighted conversion, ticket, target variance, channel metrics and a sequential revenue bridge; generated six CSV reports.
- Documented the independently reconciled synthetic results, management recommendations and limitations.
- Excluded the local performance archive from version control.
- Established cumulative Portuguese technical documentation alongside the English repository documentation.

## v0.2.0 — Commercial Profitability Analysis (2026-11-26)

- Added the locally validated profitability script, with seven CSV report outputs.
- Corrected zero-quantity validation to retain legitimate no-sale observations.
- Added weighted profitability metrics, monthly comparison, dynamic discount limits and static 0% / 5% margin scenarios.
- Documented the reconciled synthetic results, business recommendations and model limitations.
- Extended ignore rules to cover the new OAuth token and local ZIP archive.
- Verified the uploaded reports against unit, product and monthly totals.

## v0.1.0 — Automated Data Quality Validation

- Configured read-only Google Sheets OAuth access.
- Implemented the commercial data quality validator and its two CSV outputs.
- Validated the synthetic dataset locally and identified twelve negative gross profit alerts.
- Published the original source, dependency manifest and repository documentation.

Version headings identify development milestones; Git tags and formal GitHub releases are managed separately.
