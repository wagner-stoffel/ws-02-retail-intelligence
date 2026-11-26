# WS-02 | Phase 4 — SQL Data Modelling

Extract all files into the existing project root. Keep the previous two analysis modules and credentials in place. The model is scoped to complete calendar months and the full daily unit/SKU grid of this exercise.

```powershell
python test_sql_model.py
python build_retail_database.py
```

The first command runs an offline fixture (no Google authentication). The second loads a read-only snapshot using the existing OAuth connection and asks for the spreadsheet URL/ID. It validates the input using the Phase 3 module, builds a temporary SQLite database and checks referential integrity and 24 SQL/Pandas reconciliations before replacing the local snapshot. This is a rebuild, not incremental loading; do not store manual changes in the generated database.

Outputs: `data/retail_intelligence.sqlite3`, seven analytical CSVs and `reconciliation.csv` in `reports/sql/`. CSVs have UTF-8 BOM, semicolon delimiters and decimal commas. Monetary base columns are integer BRL cents. The reports show monetary metrics in BRL. NULL ratios indicate an undefined denominator.

The SQL statements can be studied in `sql/schema.sql` and `sql/queries.sql`. Use Python's `sqlite3` or any compatible SQLite client to run read-only queries. For example:

```sql
SELECT month, unit, ROUND(gross_margin_pct,2) AS margin_pct
FROM v_monthly_performance
ORDER BY month, gross_margin_pct DESC;
```

Do not publish the local database, OAuth tokens or reports. Add `/data/` and `sql_reports.zip` to `.gitignore` before any commit. The source spreadsheet is not modified. Power BI integration is a separate milestone; it can use the SQL-generated CSVs or a suitable SQLite connector.
