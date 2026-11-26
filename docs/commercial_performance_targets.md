# Commercial Performance & Targets — Phase 3

**Milestone:** v0.3.0 (26 November 2026)  
**Scope:** Synthetic retail dataset, September–October 2026.

## Business question

Which units are meeting commercial objectives, and which performance drivers merit management attention? This phase extends the previous data quality and profitability analyses by integrating sales, customer traffic and targets.

## Data model and integration

| Source | Grain | Rows |
| --- | --- | ---: |
| Vendas | Day × commercial unit × SKU | 4,392 |
| Fluxo | Day × commercial unit | 366 |
| Metas | Month × commercial unit | 12 |

The performance module reuses the read-only OAuth connection and sales preparation functions of the corrected profitability module. Sales are aggregated to day/unit before joining traffic; monthly aggregates are then joined to targets. Both joins require one-to-one cardinality and matching keys, with month-length, numeric, date and business-rule checks. Joining raw SKU rows directly to traffic would multiply visits and completed orders.

## Metrics and business rules

- Conversion = completed orders / visits or sessions.
- Average ticket = net sales after discounts / completed orders.
- Items per order = quantity / completed orders.
- Revenue per visit = net sales / visits or sessions.
- Gross margin = gross profit / net sales.
- Weighted discount = total discount / gross sales before discounts.
- Sales target attainment = net sales / target net sales.
- Margin and conversion gaps are expressed in percentage points. Profit gap is computed at actual net sales; order gap is computed at actual traffic.
- Ratios are computed from aggregate numerators and denominators, not averages of individual rates. Undefined ratios are not replaced with zero. Physical visits and digital sessions are kept separate.

The revenue bridge substitutes days, visits per day, conversion and average ticket sequentially in that order. Interactions are attributed to later factors. It is a mathematical decomposition, not a causal estimate.

## Results and validation

The locally executed module generated six CSVs. Independent reconciliation of the two submitted report archives confirmed matching financial totals across daily, monthly, channel and profitability reports to within BRL 0.01, no duplicate daily/monthly keys, matching traffic and order totals, and zero residual at the exported precision for all six revenue bridges.

| Network indicator | September | October |
| --- | ---: | ---: |
| Net sales (BRL) | 20,915,737.43 | 23,403,413.53 |
| Sales target (BRL) | 19,870,000.00 | 21,980,000.00 |
| Sales target attainment | 105.26% | 106.48% |
| Gross profit (BRL) | 3,628,722.43 | 3,538,758.03 |
| Gross margin | 17.35% | 15.12% |
| Individual targets met | 16/18 | 11/18 |

October scorecard (targets: 100% revenue attainment, 17% margin, 15% physical conversion or 2.5% digital conversion):

| Unit | Sales attainment | Gross margin | Conversion |
| --- | ---: | ---: | ---: |
| Novo Hamburgo | 100.53% | 17.05% | 14.72% |
| Porto Alegre | 120.86% | 9.90% | 16.50% |
| Caxias do Sul | 96.18% | 16.94% | 15.84% |
| Curitiba | 61.95% | 17.76% | 9.77% |
| São Paulo | 119.50% | 17.71% | 17.21% |
| E-commerce | 116.62% | 14.67% | 2.61% |

Only São Paulo met all three targets in October. The combined negative sales-target gaps for underperforming units amounted to BRL 1,261,963.23, while the net network gross-profit gap relative to the 17% margin target at actual sales was BRL 439,822.27. These gaps are not accounting losses or guaranteed recoverable benefits.

## Revenue bridge (September to October)

| Driver | Curitiba (BRL, approximate) | Porto Alegre (BRL, approximate) |
| --- | ---: | ---: |
| Days | +90,522 | +124,933 |
| Daily traffic | +464,229 | +1,585,940 |
| Conversion | -1,083,333 | -243,405 |
| Ticket | -266,469 | -489,868 |
| Net sales change | -795,051.80 | +977,601.29 |

Curitiba's daily traffic increased 16.54%, but conversion fell from 14.61% to 9.77% and average ticket declined 12.18%. Conversion was the largest negative bridge component. Porto Alegre's growth was primarily associated with traffic expansion; weaker conversion and average ticket offset part of that gain. The evidence does not establish that discounts caused the traffic growth.

## Management recommendations

| Priority | Unit | Proposed action | Monitor |
| --- | --- | --- | --- |
| P1 | Curitiba | Investigate service, availability, waiting time and abandonment. | Conversion, average ticket, revenue per visit |
| P1 | Porto Alegre | Review discount authority and cost-sensitive margin guardrails. | Gross margin, exceptions, revenue, conversion |
| P2 | E-commerce | Review campaign and pricing economics. | Gross margin by channel |
| P2 | Caxias do Sul | Investigate declining daily traffic. | Visits per day, sales attainment |
| P3 | Novo Hamburgo | Improve conversion relative to target. | Conversion |
| P3 | São Paulo | Study replicable practices and cross-selling opportunities. | Gross profit growth and ticket |

## Local outputs

| CSV (under reports/performance/) | Rows |
| --- | ---: |
| daily_performance.csv | 366 |
| monthly_performance_targets.csv | 12 |
| channel_performance.csv | 4 |
| monthly_performance_comparison.csv | 6 |
| network_financial_performance.csv | 2 |
| target_exceptions.csv | 6 |

Run `python analyze_commercial_performance.py --spreadsheet "<YOUR_SHEET_ID_OR_URL>"` after the previous modules have been configured. The six exception rows denote unit/month combinations with at least one unmet or undefined target, not six individual failed metrics. The nine failed individual targets are distributed across September (2) and October (7).

## Limitations and next milestone

Synthetic observations are aggregated by day/unit/SKU, not transaction or customer. They do not support causal conclusions about service, promotions or purchasing behaviour. The full quality-audit CSV was not independently re-opened in this documentation cycle; the earlier execution evidence and Phase 2 negative-profit detail support the reported alerts. A public reproducible dataset, broader automated tests and production controls remain pending. The next milestone is SQL modelling with separate facts at their correct grains and reconciled KPI queries.
