-- name: network_monthly
-- Financial totals only: do not pool physical visits and online sessions.
SELECT month, SUM(quantity) quantity, SUM(gross_sales_cents)/100.0 gross_sales_brl,
 SUM(discount_cents)/100.0 discount_brl, SUM(net_sales_cents)/100.0 net_sales_brl,
 SUM(cogs_cents)/100.0 cogs_brl, SUM(gross_profit_cents)/100.0 gross_profit_brl,
 100.0*SUM(gross_profit_cents)/NULLIF(SUM(net_sales_cents),0) gross_margin_pct,
 SUM(target_sales_cents)/100.0 target_sales_brl,
 100.0*SUM(net_sales_cents)/NULLIF(SUM(target_sales_cents),0) sales_attainment_pct
FROM v_monthly_performance GROUP BY month ORDER BY month;

-- name: unit_monthly_scorecard
SELECT month,unit,channel,days,quantity,visits,orders,net_sales_cents/100.0 net_sales_brl,
 gross_profit_cents/100.0 gross_profit_brl,target_sales_cents/100.0 target_sales_brl,
 sales_attainment_pct,gross_margin_pct,conversion_pct,weighted_discount_pct,average_ticket_brl,
 items_per_order,revenue_per_visit_brl,sales_gap_cents/100.0 sales_gap_brl,margin_gap_pp,conversion_gap_pp,
 sales_status,margin_status,conversion_status
FROM v_monthly_performance ORDER BY month,unit;

-- name: product_profitability
SELECT sku,product,SUM(quantity) quantity,SUM(net_sales_cents)/100.0 net_sales_brl,
 SUM(gross_profit_cents)/100.0 gross_profit_brl,
 100.0*SUM(gross_profit_cents)/NULLIF(SUM(net_sales_cents),0) gross_margin_pct
FROM v_sales GROUP BY sku,product ORDER BY gross_profit_brl DESC;

-- name: channel_monthly
SELECT month,channel,SUM(visits) visits,SUM(orders) orders,
 SUM(net_sales_cents)/100.0 net_sales_brl,SUM(gross_profit_cents)/100.0 gross_profit_brl,
 100.0*SUM(orders)/NULLIF(SUM(visits),0) conversion_pct,
 SUM(net_sales_cents)/100.0/NULLIF(SUM(orders),0) average_ticket_brl,
 100.0*SUM(gross_profit_cents)/NULLIF(SUM(net_sales_cents),0) gross_margin_pct,
 100.0*SUM(net_sales_cents)/NULLIF(SUM(target_sales_cents),0) sales_attainment_pct
FROM v_monthly_performance GROUP BY month,channel ORDER BY month,channel;

-- name: target_exceptions
SELECT month,unit,sales_status,margin_status,conversion_status,
 sales_gap_cents/100.0 sales_gap_brl,margin_gap_pp,conversion_gap_pp
FROM v_monthly_performance WHERE sales_status<>'MET' OR margin_status<>'MET' OR conversion_status<>'MET'
ORDER BY month,unit;

-- name: negative_profit_details
SELECT source_row,date,unit,sku,product,quantity,net_sales_cents/100.0 net_sales_brl,
 cogs_cents/100.0 cogs_brl,gross_profit_cents/100.0 gross_profit_brl
FROM v_sales WHERE gross_profit_cents<0 ORDER BY source_row;

-- name: unit_monthly_change
WITH previous AS (
 SELECT month,unit,net_sales_cents,gross_profit_cents,gross_margin_pct,conversion_pct,
 LAG(month) OVER (PARTITION BY unit ORDER BY month) previous_month,
 LAG(net_sales_cents) OVER (PARTITION BY unit ORDER BY month) prev_sales,
 LAG(gross_profit_cents) OVER (PARTITION BY unit ORDER BY month) prev_profit,
 LAG(gross_margin_pct) OVER (PARTITION BY unit ORDER BY month) prev_margin,
 LAG(conversion_pct) OVER (PARTITION BY unit ORDER BY month) prev_conversion
 FROM v_monthly_performance
)
SELECT month,unit,previous_month,(net_sales_cents-prev_sales)/100.0 sales_change_brl,
 100.0*(net_sales_cents-prev_sales)/NULLIF(prev_sales,0) sales_change_pct,
 (gross_profit_cents-prev_profit)/100.0 gross_profit_change_brl,
 gross_margin_pct-prev_margin margin_change_pp,conversion_pct-prev_conversion conversion_change_pp
FROM previous WHERE previous_month IS NOT NULL ORDER BY month,unit;
