# Data Dictionary

## `firms.csv`
Synthetic firms in the execution-liquidity graph.

| Column | Meaning |
|---|---|
| firm_id | Synthetic firm identifier |
| sector | Sector label |
| size_class | SME / mid / large / anchor |
| annual_revenue_mrub | Annual revenue, million RUB |
| initial_cash_buffer_mrub | Initial liquidity buffer, million RUB |
| pd_12m | Synthetic 12-month probability of default |
| supplier_criticality | Structural importance as supplier, 0..1 |

## `execution_edges.csv`
Supplier-buyer execution links.

| Column | Meaning |
|---|---|
| edge_id | Synthetic contract edge identifier |
| supplier_id | Supplier node |
| buyer_id | Buyer node |
| annual_contract_mrub | Contract amount, million RUB |
| payment_term_days | Contractual payment term |
| delay_risk | Probability-like delay risk parameter |
| execution_dependency | Dependency strength between firms |

## `obligations.csv`
Generated invoices and payments.

## `liquidity_timeseries.csv`
Firm-period liquidity states.

## `interventions.csv`
Top bottleneck financing interventions selected by the liquidity-operator heuristic.

## `simulation_results.csv`
Traditional vs execution-aware simulation curves.
