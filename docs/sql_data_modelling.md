# SQL Data Modelling — Phase 4

**Milestone:** v0.4.0 — 26 November 2026  
**Scope:** Synthetic retail dataset; September–October 2026.

## Business objective

Establish a local, relational analytical layer for repeatable commercial indicators and future business intelligence. SQLite was selected for the MVP because it requires no database server or additional Python dependency. This is not a multi-user production deployment.

## Model and grain

| Object | Grain | Expected rows |
| --- | --- | ---: |
| dim_month | Calendar month | 2 |
| dim_date | Calendar day | 61 |
| dim_unit | Commercial unit | 6 |
| dim_product | SKU | 12 |
| fact_sales | Date × unit × SKU | 4,392 |
| fact_traffic | Date × unit | 366 |
| fact_targets | Month × unit | 12 |

The fact constellation shares conformed dimensions. Composite primary keys enforce uniqueness, foreign keys enforce valid references, and CHECK constraints restrict quantities, prices, costs, discounts, traffic and targets. Monetary base fields are integer BRL cents. Percentage ratios remain floating point; NULL represents an undefined denominator. Sales are aggregated to day/unit before joining traffic and to month/unit before joining targets. This avoids multiplying traffic or targets by SKU.

## Implementation and controls

The loader reuses Phase 2 OAuth and sales preparation and Phase 3 validation. It reads Google Sheets with read-only access, validates the full daily unit/SKU grid, checks consistent unit and product attributes, creates a temporary SQLite database, loads dimensions and facts using parameterised INSERT statements, and runs integrity checks and SQL/Pandas reconciliation. It replaces the previous local snapshot only after validation and SQL query execution succeed. CSV output follows database replacement; a CSV write failure may therefore require a rerun. The implementation performs full snapshot rebuilds rather than incremental updates.

The three views are `v_sales`, `v_daily_performance` and `v_monthly_performance`. Seven named queries in `sql/queries.sql` use aggregation, joins, CTEs and LAG window functions for analysis. `test_sql_model.py` contains an offline integration fixture covering loading, zero-sale observations, invalid foreign keys, duplicate keys, discount constraints and preservation of the previous database after failed validation.

## Execution evidence

The user successfully executed a query against v_monthly_performance using Python's SQLite command-line shell, returning all twelve expected unit/month gross margins. An earlier VS Code SQLite extension failed to open the catalogue because of its double-quoted string-literal query; the direct SQLite shell worked independently of that extension.

The submitted SQL archive contained all eight expected CSV reports. All 24 recorded reconciliation controls returned OK. Independent comparison against the previously submitted profitability and performance archives confirmed matching report keys and common comparable metrics. Monetary values matched to the cent; the maximum product-margin difference was approximately 0.000049 percentage points, consistent with different export precision.

| Report | Rows |
| --- | ---: |
| network_monthly.csv | 2 |
| unit_monthly_scorecard.csv | 12 |
| product_profitability.csv | 12 |
| channel_monthly.csv | 4 |
| target_exceptions.csv | 6 |
| negative_profit_details.csv | 12 |
| unit_monthly_change.csv | 6 |
| reconciliation.csv | 24 |

| Consolidated metric | Result |
| --- | ---: |
| Quantity | 12,253 |
| Gross sales | BRL 46,839,327.00 |
| Discounts | BRL 2,520,176.04 |
| Net sales after discounts | BRL 44,319,150.96 |
| COGS | BRL 37,151,670.50 |
| Gross profit | BRL 7,167,480.46 |
| Gross margin | 16.17% |
| Sales targets | BRL 41,850,000.00 |
| Negative-profit observations | 12 |
| Loss on negative-profit observations | BRL 3,988.79 |

The actual database file was not supplied for independent inspection in this documentation cycle; validation is based on the exported reports, the source package and the observed execution evidence. Results relate solely to synthetic data.

## Operation and next milestone

See [SQL setup](../SQL_SETUP.md). Run the offline test before building the database; then use the existing OAuth credentials to load the snapshot. The database, generated reports and local archive remain excluded from version control.

Next: an executive Power BI dashboard. A SQL-derived export at appropriate fact grains or a compatible SQLite connector will be evaluated. The BI model must recalculate ratios from their numerators and denominators, retain separate grains and avoid aggregating physical visits with digital sessions. A production database, incremental loads, concurrency, access controls and broader test coverage are future considerations.
