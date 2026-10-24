# Numerical and evidence corrections — 24 October 2026

The previous `make_results` ignored its intervention argument and multiplied a baseline by a preset improvement curve. Those curves were illustrative assumptions, not simulated policy outcomes. The previous favorable comparison is withdrawn and must not be used as evidence of graph-aware lending effectiveness. The stored data and figures in this revision have been regenerated.

The previous cash-tension calculation first updated/clipped cash and then subtracted obligations again, using closing cash where opening liquidity was required. The corrected ledger calculates each flow once and carries signed uncovered funding needs forward.

The replacement comparison uses the same cash schedules and equal budgets for a borrower-score policy and a graph-score policy, with explicit one-off drawings and bullet repayments. Selection uses pre-decision observations only. Money allocation uses integer subunits to avoid exceeding the budget through independent rounding. Zero funding produces zero effect.

The corrected default run does not establish graph-score superiority: deficit-exposure reduction is 14,522.24 million RUB × periods for the borrower score and 11,764.86 for the graph score. Both draw and repay 2,500.00 million RUB. These are conditional synthetic outputs, not empirical effects.

The uncalibrated `collapse_probability` column has been replaced by `synthetic_stress_index`. The obligation field formerly called `actual_payment_period` is now `scheduled_payment_period`, because no real payment observations are present. Data consumers must use the corrected column names and interpretations in `DATA_DICTIONARY.md`.

Ten focused regression/invariant tests cover zero effect, dependence on the actual funded recipient, opening-cash arithmetic, cash/debt conservation, maturity, horizon boundaries, budget rounding, information cutoff, missing-comparator labeling, paired internal transfers and rejection of invalid inputs. The checks do not validate the realism of the generated economy or a causal network mechanism.
