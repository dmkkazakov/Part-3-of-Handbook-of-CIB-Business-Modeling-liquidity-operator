# Data dictionary

Money is in million RUB. Time is a monthly period numbered from zero. All inputs are synthetic.

## firms.csv

| Column | Meaning |
|---|---|
| firm_id | Unique synthetic firm identifier |
| sector, size_class | Generated categorical attributes |
| annual_revenue_mrub | Size proxy; used to generate operating outflows, not booked as external receipts |
| initial_cash_buffer_mrub | Opening net liquidity before period 0 |
| pd_12m | Synthetic ranking/index input; no observed default calibration |
| supplier_criticality | Generated graph-score input in [0,1] |

## execution_edges.csv and obligations.csv

Edges identify supplier/buyer pairs, annual contract-size inputs, terms, delay parameters and synthetic dependency labels. The dependency label does not drive payment feedback.

Each obligation records the generation `period`, `edge_id`, supplier, buyer, `invoice_amount_mrub`, `contractual_due_period`, `scheduled_payment_period` and `is_delayed`. The scheduled date is generated, not an observed actual-payment date. It can lie beyond the reporting horizon. The same invoice amount is used in the buyer's and supplier's schedules.

## liquidity_timeseries.csv

| Column | Meaning |
|---|---|
| firm_id, period | Unique firm/period key |
| opening_cash_mrub | Opening signed net-liquidity position |
| cash_buffer_mrub | Closing signed net liquidity; negative values mean uncovered funding needs |
| obligations_mrub | Scheduled invoice outflows plus external operating outflows |
| inflows_mrub | Scheduled invoice receipts |
| external_operating_outflow_mrub | Part of obligations leaving the modeled network |
| cash_tension_mrub | max(0, -closing net liquidity) |
| pd_12m | Synthetic input for the illustrative stress index |
| synthetic_stress_index | Uncalibrated logistic index, not a collapse/default probability |

## interventions.csv and borrower_interventions.csv

Both contain `firm_id`, `policy`, `operator_type`, `intervention_amount_mrub`, `start_period`, `tenor_periods`, `allocation_score`, `historical_tension_exposure`, `supplier_exposure_mrub` and `supplier_out_degree`. `operator_type` is always the implemented zero-interest bullet loan. Historical tension exposure uses only dates preceding the decision. Funding is not differentiated into factoring, guarantees or revolving products.

## liquidity_graph_score.csv and liquidity_borrower_centric.csv

The fixed schedule is replayed with each policy. Additional columns expose `credit_draw_mrub`, `principal_repayment_mrub`, `opening_debt_mrub` and `closing_debt_mrub`. The cash/debt identities can be checked row by row.

## simulation_results.csv

One row per period, with `no_credit_`, `borrower_centric_` and `graph_score_` prefixes. Each has `avg_stress_index`, `total_tension_mrub`, `credit_draw_mrub`, `principal_repayment_mrub` and `closing_debt_mrub`. All are aggregates of the corresponding replay, not synthetic uplift factors.

## processed outputs

`firm_scores.csv` records rankings and `decision_period`. `baseline_summary.csv` records principal, terminal debt, peak tension, deficit exposure and the illustrative stress index. Deficit exposure and its reduction have units million RUB × periods; summing a deficit stock does not produce a financing budget.

`experiment_metadata.json` records seed, dimensions, budget, timing and the absence of payment feedback or default calibration.
