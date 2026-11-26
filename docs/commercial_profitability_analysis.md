# Commercial Profitability Analysis — Phase 2

**Project:** WS-02 Retail Intelligence  
**Milestone:** v0.2.0  
**Period:** September–October 2026  
**Dataset:** synthetic consumer electronics retail observations, six commercial units and twelve SKUs.

## 1. Business question

Why did the simulated Porto Alegre store report negative gross profit on twelve daily SKU observations in October, and how can management protect profitability while maintaining commercial performance?

The analysis follows the Phase 1 data quality audit. A negative gross profit is a commercial alert, not automatically a data error. No rows were deleted and the source spreadsheet was not modified.

## 2. Method and validation

The Python module reads sales data through Google Sheets API with read-only OAuth scope and aggregates it with pandas. A record represents a daily unit/SKU observation, not necessarily an individual customer order.

- Gross sales = quantity × list price.
- Net sales = gross sales − total discount (before any unmodelled taxes or deductions).
- Cost of goods sold (COGS) = quantity × unit cost.
- Gross profit = net sales − COGS.
- Gross margin = total gross profit / total net sales.
- Weighted discount = total discounts / total gross sales.

The module accepts zero quantities when the discount is also zero. Negative or fractional quantities, non-positive list prices, negative costs or discounts, and discounts exceeding gross sales are rejected. The correction reconciled the business rule with Phase 1. A controlled test verified zero-sale handling, negative gross profit, discount simulation and generation of seven reports; the complete dataset was processed successfully in the local environment.

Reconciliation of the seven exported CSVs confirmed the same totals by unit, product and month. The negative-record detail reconciled to the reported gross loss of BRL 3,988.79. This is not an exhaustive audit of production readiness.

## 3. Consolidated performance

| Metric | September | October | Change |
| --- | ---: | ---: | ---: |
| Net sales (BRL) | 20,915,737.43 | 23,403,413.53 | +11.89% |
| Gross profit (BRL) | 3,628,722.43 | 3,538,758.03 | −2.48% |
| Gross margin | 17.35% | 15.12% | −2.23 pp |
| Discounts (BRL) | 892,669.57 | 1,627,506.47 | +82.32% |
| Units sold | 5,493 | 6,760 | +23.07% |

Commercial growth did not translate into greater gross profit. Gross profit decreased by BRL 89,964.40 despite higher sales. The periods have different numbers of days, and the observed changes do not establish causality.

### Unit comparison (two-month totals)

| Unit | Net sales (BRL) | Gross profit (BRL) | Gross margin |
| --- | ---: | ---: | ---: |
| E-commerce | 12,285,653.82 | 1,943,097.82 | 15.82% |
| São Paulo | 9,825,806.02 | 1,729,678.52 | 17.60% |
| Porto Alegre | 8,473,591.29 | 1,116,508.79 | 13.18% |
| Novo Hamburgo | 4,845,120.90 | 841,500.90 | 17.37% |
| Curitiba | 4,636,259.48 | 813,013.48 | 17.54% |
| Caxias do Sul | 4,252,719.45 | 723,680.95 | 17.02% |

São Paulo combined strong net sales growth with improved margin. Curitiba experienced a sharp sales contraction. E-commerce grew in gross profit but experienced margin compression. Porto Alegre is the priority for a profitability review.

## 4. Porto Alegre diagnosis

| Metric | September | October |
| --- | ---: | ---: |
| Net sales (BRL) | 3,747,995.00 | 4,725,596.29 |
| Gross profit (BRL) | 648,775.00 | 467,733.79 |
| Gross margin | 17.31% | 9.90% |
| Weighted discount | 4.16% | 11.93% |
| Discounts (BRL) | 162,818.00 | 639,906.71 |
| Units sold | 987 | 1,397 |
| Negative gross profit observations | 0 | 12 |

All 12 deficit records are concentrated in this simulated physical store in October. They cover 54 units and four SKUs, with a total gross loss of BRL 3,988.79. The iPhone 17 Pro accounts for BRL 2,462.41 of this loss. Discounts exceeded break-even on all flagged rows.

Higher discounts are a directly observed factor in the flagged losses, but the underlying management decisions and the relative effects of product mix and costs remain unverified. The dataset does not establish whether discounts were authorised promotions or operational deviations.

## 5. Product economics and pricing guardrails

The highest gross profit contributions come from iPhones, while accessories have higher percentage margins (e.g. 62.36% for the phone case and 59.74% for the USB-C charger). Cross-selling is a hypothesis to test; order-level or basket data is required before drawing conclusions.

The maximum discount rate for a feasible target gross margin m (expressed as a fraction) is:

    max_discount = 1 − unit_cost / (unit_price × (1 − m))

A negative ceiling means the target cannot be achieved at the list price. The script flags infeasible combinations instead of treating zero discount as a guaranteed solution. The twelve SKUs produce fourteen distinct observed price/cost combinations because the two MacBook SKUs each have two costs. A dynamic guardrail is therefore preferable to assuming a fixed ceiling per SKU regardless of cost.

## 6. Static what-if analysis

October, Porto Alegre:

| Scenario | Adjusted records | Gross profit (BRL) | Gross margin | Uplift (BRL) |
| --- | ---: | ---: | ---: | ---: |
| Actual simulated data | 0 | 467,733.79 | 9.90% | — |
| Minimum margin of 0% | 12 | 471,722.58 | 9.97% | 3,988.79 |
| Minimum margin of 5% | 80 | 532,754.82 | 11.12% | 65,021.03 |

Quantities and costs are held constant. The 5% row-level minimum is an experimental assumption, not an approved policy. Even under that scenario, gross profit remains below September. A simplified proportional volume sensitivity implies that a reduction of approximately 12.20% would eliminate the simulated gross profit advantage; this is a break-even sensitivity, not a demand forecast.

## 7. Proposed management actions

| Priority | Action | Measurement |
| --- | --- | --- |
| Immediate | Introduce review of discounts that create negative gross profit. | Negative-profit records and gross loss |
| High | Investigate Porto Alegre discount authorisations, campaign rules and mix. | Gross margin and weighted discount |
| High | Compare São Paulo and Porto Alegre practices. | Net sales and gross profit growth |
| High | Pilot cost-sensitive pricing guardrails with human approval of exceptions. | Margin, conversion, volume and exception rate |
| Medium | Review Curitiba sales contraction and e-commerce margin compression. | Net sales, gross margin and conversion |
| Medium | Assess accessory cross-selling with order-level data. | Attachment rate and gross profit per basket |

## 8. Limitations and next phase

- These are synthetic results, not evidence of the performance of any real retailer.
- The simulations do not account for price elasticity, changing volumes or product mix, operating expenses, taxes, or campaign funding.
- Daily observations are not transaction-level or customer-level records.
- The monthly comparison code is scoped to September–October 2026; broader period support and production-grade validation remain future work.
- A reproducible demonstration dataset and expanded automated tests remain pending.
- Next phase: analyse commercial targets, visits/sessions, conversion and target attainment, maintaining read-only access to the source data.
