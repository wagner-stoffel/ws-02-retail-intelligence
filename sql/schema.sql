-- WS-02 | SQLite analytical model. Monetary values are integer BRL cents.
PRAGMA foreign_keys = ON;
CREATE TABLE dim_month (
    month TEXT PRIMARY KEY NOT NULL CHECK (month GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'),
    days_in_month INTEGER NOT NULL CHECK (days_in_month BETWEEN 28 AND 31)
);
CREATE TABLE dim_date (
    date TEXT PRIMARY KEY NOT NULL,
    month TEXT NOT NULL REFERENCES dim_month(month),
    CHECK (substr(date,1,7)=month)
);
CREATE TABLE dim_unit (
    unit TEXT PRIMARY KEY NOT NULL, region TEXT NOT NULL, channel TEXT NOT NULL
);
CREATE TABLE dim_product (
    sku TEXT PRIMARY KEY NOT NULL, category TEXT NOT NULL, product TEXT NOT NULL
);
CREATE TABLE fact_sales (
    date TEXT NOT NULL REFERENCES dim_date(date),
    unit TEXT NOT NULL REFERENCES dim_unit(unit),
    sku TEXT NOT NULL REFERENCES dim_product(sku),
    source_row INTEGER NOT NULL UNIQUE CHECK(source_row>=2),
    quantity INTEGER NOT NULL CHECK(typeof(quantity)='integer' AND quantity>=0),
    unit_price_cents INTEGER NOT NULL CHECK(typeof(unit_price_cents)='integer' AND unit_price_cents>0),
    discount_cents INTEGER NOT NULL CHECK(typeof(discount_cents)='integer' AND discount_cents>=0 AND discount_cents<=quantity*unit_price_cents),
    unit_cost_cents INTEGER NOT NULL CHECK(typeof(unit_cost_cents)='integer' AND unit_cost_cents>=0),
    PRIMARY KEY(date,unit,sku)
);
CREATE TABLE fact_traffic (
    date TEXT NOT NULL REFERENCES dim_date(date),
    unit TEXT NOT NULL REFERENCES dim_unit(unit),
    visits INTEGER NOT NULL CHECK(typeof(visits)='integer' AND visits>=0),
    orders INTEGER NOT NULL CHECK(typeof(orders)='integer' AND orders BETWEEN 0 AND visits),
    PRIMARY KEY(date,unit)
);
CREATE TABLE fact_targets (
    month TEXT NOT NULL REFERENCES dim_month(month),
    unit TEXT NOT NULL REFERENCES dim_unit(unit),
    target_sales_cents INTEGER NOT NULL CHECK(typeof(target_sales_cents)='integer' AND target_sales_cents>0),
    target_margin_rate REAL NOT NULL CHECK(target_margin_rate BETWEEN 0 AND 1),
    target_conversion_rate REAL NOT NULL CHECK(target_conversion_rate BETWEEN 0 AND 1),
    PRIMARY KEY(month,unit)
);
CREATE INDEX idx_sales_unit_date ON fact_sales(unit,date);
CREATE INDEX idx_sales_sku ON fact_sales(sku);

CREATE VIEW v_sales AS
SELECT s.*, d.month, u.region, u.channel, p.category, p.product,
       quantity*unit_price_cents AS gross_sales_cents,
       quantity*unit_price_cents-discount_cents AS net_sales_cents,
       quantity*unit_cost_cents AS cogs_cents,
       quantity*(unit_price_cents-unit_cost_cents)-discount_cents AS gross_profit_cents
FROM fact_sales s JOIN dim_date d USING(date) JOIN dim_unit u USING(unit) JOIN dim_product p USING(sku);

-- Aggregate before joining facts: one row per day/unit on both sides.
CREATE VIEW v_daily_performance AS
WITH sales AS (
  SELECT date,unit,SUM(quantity) quantity,SUM(gross_sales_cents) gross_sales_cents,
         SUM(discount_cents) discount_cents,SUM(net_sales_cents) net_sales_cents,
         SUM(cogs_cents) cogs_cents,SUM(gross_profit_cents) gross_profit_cents,
         SUM(CASE WHEN gross_profit_cents<0 THEN 1 ELSE 0 END) negative_records
  FROM v_sales GROUP BY date,unit
)
SELECT s.*,d.month,u.region,u.channel,t.visits,t.orders
FROM sales s JOIN fact_traffic t USING(date,unit) JOIN dim_date d USING(date) JOIN dim_unit u USING(unit);

CREATE VIEW v_monthly_performance AS
WITH m AS (
 SELECT month,unit,region,channel,COUNT(*) days,SUM(quantity) quantity,
        SUM(gross_sales_cents) gross_sales_cents,SUM(discount_cents) discount_cents,
        SUM(net_sales_cents) net_sales_cents,SUM(cogs_cents) cogs_cents,
        SUM(gross_profit_cents) gross_profit_cents,SUM(negative_records) negative_records,
        SUM(visits) visits,SUM(orders) orders
 FROM v_daily_performance GROUP BY month,unit,region,channel
), k AS (
 SELECT m.*,t.target_sales_cents,t.target_margin_rate,t.target_conversion_rate,
    100.0*m.net_sales_cents/NULLIF(t.target_sales_cents,0) sales_attainment_pct,
    100.0*m.gross_profit_cents/NULLIF(m.net_sales_cents,0) gross_margin_pct,
    100.0*m.orders/NULLIF(m.visits,0) conversion_pct,
    100.0*m.discount_cents/NULLIF(m.gross_sales_cents,0) weighted_discount_pct,
    m.net_sales_cents/100.0/NULLIF(m.orders,0) average_ticket_brl,
    1.0*m.quantity/NULLIF(m.orders,0) items_per_order,
    m.net_sales_cents/100.0/NULLIF(m.visits,0) revenue_per_visit_brl,
    m.net_sales_cents-t.target_sales_cents sales_gap_cents
 FROM m JOIN fact_targets t USING(month,unit)
)
SELECT k.*,gross_margin_pct-100*target_margin_rate margin_gap_pp,
       conversion_pct-100*target_conversion_rate conversion_gap_pp,
       CASE WHEN sales_gap_cents>=0 THEN 'MET' ELSE 'BELOW' END sales_status,
       CASE WHEN gross_margin_pct IS NULL THEN 'UNDEFINED' WHEN gross_margin_pct+1e-8>=100*target_margin_rate THEN 'MET' ELSE 'BELOW' END margin_status,
       CASE WHEN conversion_pct IS NULL THEN 'UNDEFINED' WHEN conversion_pct+1e-8>=100*target_conversion_rate THEN 'MET' ELSE 'BELOW' END conversion_status
FROM k;
