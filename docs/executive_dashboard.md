# Phase 5 — Executive Dashboard (v0.5.0 candidate)

## Business objective

Provide managers with an interactive view of revenue, profitability, traffic, commercial targets and actionable exceptions, using the same validated analytical layer as the SQL milestone.

## Implemented report

The submitted and corrected PBIP source contains five pages, 46 visual definitions and 31 DAX measures. It preserves four business dimensions, three fact tables and eight planned business relationships, plus an automatic date-table relationship. The submitted report includes a custom theme, monthly comparisons, an executive summary, conditional formatting and an automated commercial priority classification.

| Page | Visual definitions | Business purpose |
| --- | ---: | --- |
| Executive Overview | 10 | Consolidated financial results and target attainment |
| Store Performance | 9 | Unit-level comparison and performance exceptions |
| Profitability & Pricing | 9 | Margins, discounts and loss-making observations |
| Commercial Funnel | 9 | Traffic, orders, conversion and average ticket |
| Targets & Action Plan | 9 | Target gaps and rule-based prioritisation |

## Data preparation and semantic model

Run `python export_powerbi_data.py` after building the validated SQLite database. The exporter opens SQLite read-only, checks database integrity and references, then writes seven UTF-8 BOM semicolon-delimited CSVs with ISO dates and decimal-point rates to `data/powerbi/`. Monetary columns remain integer BRL cents. Financial totals, traffic and revenue targets are reconciled against the source before the staged exports replace the prior CSVs.

| Query | Grain | Expected rows |
| --- | --- | ---: |
| dim_month | Month | 2 |
| dim_date | Date | 61 |
| dim_unit | Commercial unit | 6 |
| dim_product | SKU | 12 |
| fact_sales | Date × unit × SKU | 4,392 |
| fact_traffic | Date × unit | 366 |
| fact_targets | Month × unit | 12 |

The seven Power Query (M) partitions read the corresponding CSVs from the original Windows project path (`D:\Projects\WS\WS-02 Retail Intelligence\data\powerbi`). Types are declared in the semantic model. Users with a different path must edit the source steps in Power Query. The seven CSVs, SQLite database and OAuth credentials are not distributed.

The model shares conformed dimensions; sales, traffic and targets retain separate grains. The revenue-target measure suppresses results under day or product filters because there are no corresponding targets. Revenue and cost measures convert integer cents to BRL; gross margin is calculated as gross profit divided by net sales rather than averaging row-level ratios.

## DAX measures

All 31 measures reside in fact_sales.tmdl. The following names are retained from the actual Portuguese report.

| Group | Measures |
| --- | --- |
| Financial | Faturamento; CMV; Lucro Bruto; Margem Bruta; Vendas Brutas; Descontos; Taxa de Desconto; Unidades Vendidas |
| Targets | Meta Faturamento; Atingimento da Meta; Meta Margem Bruta; Desvio Margem PP; Desvio Faturamento; Desvio Atingimento PP; Meta Conversao; Desvio Conversao PP; Unidades Abaixo da Meta |
| Commercial funnel | Visitas; Pedidos; Conversao; Ticket Medio; Receita por Visitante |
| Exceptions | Linhas Deficitarias; Perda Linhas Deficitarias; Prioridade Comercial |
| Comparison and executive reporting | Variacao Mensal Faturamento; Variacao Mensal Lucro Bruto; Sintese Executiva; Cor Margem Bruta; Cor Atingimento; Cor Barras Margem |

### Correction

The corrected TMDL contains:

```dax
Visitas =
IF(
    HASONEVALUE(dim_unit[channel]),
    SUM(fact_traffic[visits]),
    BLANK()
)
```

The dependent Conversao and Receita por Visitante measures divide by Visitas without an alternative result, so the intended outcome is blank when physical visits and digital sessions would otherwise be combined. The original and corrected source archives were compared; only fact_sales.tmdl changed. The automatic priority rules are an analytical aid, not a replacement for the management priorities in Phase 3.

## Validation and acceptance

Static inspection confirmed the five pages, visual definitions, DAX measures, source partitions and relationships. The corrected source package contains 75 versionable files matching the corrected project byte for byte; four local .pbi files, including cache.abf, are excluded.

The following values are SQL reference results, not independently observed Power BI output:

| Filter | Expected result |
| --- | --- |
| All periods: net sales | BRL 44,319,150.96 |
| All periods: gross profit | BRL 7,167,480.46 |
| All periods: gross margin | 16.17% |
| All periods: sales target | BRL 41,850,000.00 |
| October: net sales | BRL 23,403,413.53 |
| October: gross margin | 15.12% |
| October: Porto Alegre gross margin | 9.90% |
| October: physical conversion | 15.15% |
| October: digital conversion | 2.61% |
| Multiple channels: conversion | Blank |

An independent DAX engine execution and rendering in Power BI Desktop have not been performed in this environment. Verify the corrected channel filter behaviour, KPI values, visual interactions and target filter grain before final acceptance. Source-path parametrisation and broader filter-context tests are recommended.

## Running locally

The source publication target is `powerbi/executive_dashboard/`. Once the PBIP files are present, open `WS-02 Retail Intelligence.pbip` with a compatible Power BI Desktop version, adjust the seven CSV paths if necessary and refresh the model. Generated data, local settings and cache files must remain outside Git.

This is a portfolio project using synthetic data, not an actual deployment at iPlace or Apple.
