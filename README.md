# Corporate Credit as a Liquidity Operator

Synthetic execution/liquidity schedules and a reproducible comparison of two funding-allocation heuristics. The current implementation replays actual cash arithmetic; it does not insert a preset improvement curve.

## What is implemented

- Firms and directed supplier/buyer invoice links.
- Fixed stochastic payment schedules, identical under every policy.
- Signed net liquidity, uncovered funding needs and explicit loan principal.
- No credit, borrower-score allocation and graph-score allocation.
- The two funded policies have the same budget, number of recipients, start date and tenor.
- Regression tests for cash/debt conservation, zero intervention, timing, budget rounding and information cutoff.

The graph score combines historical deficit exposure, supplier exposure, out-degree and a synthetic criticality input. It is a ranking heuristic, not an estimate of a marginal causal effect. Payments do not respond endogenously to distress, and funding a supplier does not automatically change a customer's payment. The experiment therefore does **not** establish a network-propagation or graph-causal advantage.

## Reproduce

Python 3.10 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/generate_synthetic.py --firms 500 --edges 3200 --periods 26 --seed 42
python src/run_baselines.py
python src/visualize.py
```

Default settings: 500 firms, 3,200 links, 26 monthly periods numbered 0–25, a separate RUB 2,500 million budget for each funded policy and 35 recipients. Allocation uses only periods before 13. Principal is drawn once in period 13 and repaid in period 19 (six-period tenor). Interest is zero; product-specific fees, collateral, default and refinancing are outside this benchmark. `--budget`, `--targets`, `--decision-period` and `--tenor-periods` change these assumptions.

## Correct financial interpretation

```text
closing_net_liquidity = opening_net_liquidity + scheduled_receipts
                       - scheduled_outflows + principal_draw - principal_repayment
closing_debt = opening_debt + principal_draw - principal_repayment
cash_tension = max(0, -closing_net_liquidity)
```

Net liquidity can be negative. It records funding still needed, not an authorised overdraft or evidence that unfunded scheduled payments settled. Internal invoice transfers are paired, and external operating outflows reduce system liquidity. The generator does not add external customer receipts, so it deliberately produces a liquidity-depletion stress case. It is not a calibrated model of an actual corporate economy.

`cash_tension` is a stock at each date. Its sum over periods measures **deficit exposure in million RUB × periods**; it is not an additional cash expenditure or an amount of money saved. After a zero-interest loan is repaid, net-liquidity paths return to the no-credit path in this model. Unrepaid principal at the reporting horizon is disclosed.

A logistic transformation is retained as `synthetic_stress_index` for illustration. It has no empirical default calibration and is not a measured collapse probability.

## Result for the documented seed

These numbers are computed from the corrected ledgers in `data/processed/baseline_summary.csv`.

| Policy | Principal drawn, million RUB | Principal repaid, million RUB | Reduction in deficit exposure, million RUB × periods |
|---|---:|---:|---:|
| No credit | 0.00 | 0.00 | 0.00 |
| Borrower score | 2,500.00 | 2,500.00 | 14,522.24 |
| Graph score | 2,500.00 | 2,500.00 | 11,764.86 |

**The graph-score policy does not beat the borrower-score policy on deficit exposure in this run.** The arbitrary stress index gives a different ordering, illustrating metric sensitivity rather than establishing superiority. No parameter search was used to reverse this result. A single synthetic seed cannot support a general policy recommendation.

## Files

- `data/raw/`: firms, invoice links, obligations, the fixed no-credit schedule, both allocation tables, both funded ledgers and per-period comparisons.
- `data/raw/experiment_metadata.json`: seed, budget, dates, tenor and modeling boundaries.
- `data/processed/`: pre-decision scores and measured policy summary.
- `figures/`: regenerated curves and allocation charts. The historical filename `collapse_probability_baseline.png` is retained, but its content now explicitly shows an **uncalibrated synthetic index**.
- `docs/METHOD_NOTE.md`, `docs/DATA_DICTIONARY.md`: assumptions and column meanings.
- `docs/CORRECTIONS.md`: withdrawal of the prior preset-effect comparison and the numerical fixes.
- `tests/`: invariant and regression checks.

This repository is a synthetic research demonstration, not a validated credit decision or regulatory model. `CITATION.cff` contains citation metadata. Code and data are licensed under MIT.
