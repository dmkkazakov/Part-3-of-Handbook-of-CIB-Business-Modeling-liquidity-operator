# Method note: finite-budget synthetic liquidity interventions

## Model scope

The conceptual question is whether the location and timing of funding matter. The implemented test is narrower: two recipient-ranking heuristics are replayed against exactly the same externally specified cash schedules. The graph enters the graph-score ranking; it does not provide a dynamic feedback mechanism in the ledger.

The data generator draws invoices on supplier/buyer edges and fixes their scheduled payment dates, including synthetic delays. The same rounded invoice amount enters the buyer's outflow and supplier's receipt on the same date. External operating outflows are separate. The generator does not model external customer receipts, default, payment refusal, contract termination or production. Scheduled transfers must not be interpreted as settled payments when funding is insufficient.

## Net-liquidity accounting

For firm i and period t, L is signed net liquidity, R scheduled receipts, O scheduled outflows, D loan drawings, P principal repayments and B debt:

```text
L_i(t) = L_i(t-1) + R_i(t) - O_i(t) + D_i(t) - P_i(t)
B_i(t) = B_i(t-1) + D_i(t) - P_i(t)
T_i(t) = max(0, -L_i(t))
```

This uses opening liquidity exactly once. It carries uncovered funding needs forward instead of discarding them by clipping cash to zero. Negative L is a projected funding gap, not an implicit additional facility. The sign convention and all per-period draw/repayment amounts are exposed in the saved funded ledgers.

The model starts with no bank debt. Each chosen loan is drawn once at `start_period`; principal is repaid at `start_period + tenor_periods`. Repayment remains scheduled even when liquidity is negative. Interest is explicitly zero. A loan starting after the observed horizon is not drawn. Pre-history loans are rejected because no opening-debt reconstruction is implemented. Outstanding debt at the horizon is reported.

## Policy comparison and information

Default decision period is 13 in a 26-period experiment. Only observations with `period < decision_period` enter ranking. Static graph inputs and synthetic firm characteristics are assumed known at the decision date. No post-decision tension enters the selection.

Graph score:

```text
0.45 × rank(historical deficit exposure)
+ 0.25 × rank(supplier contract exposure)
+ 0.20 × rank(supplier out-degree)
+ 0.10 × rank(synthetic supplier criticality)
```

Borrower score:

```text
0.65 × rank(annual revenue) + 0.35 × (1 - rank(synthetic PD input))
```

Ranks are fractional ranks. Each policy selects the same number of firms and allocates the same total principal in proportion to its score. Largest-remainder allocation in 0.01-million-RUB units prevents independent rounding from exceeding the budget. Fractional units below 0.01 are not allocated.

Neither score solves `argmax dR/dF`, and the graph score is not a learned or causal estimate of network restoration. Default loan assumptions are identical under both policies.

## Outcomes

1. Per-period total uncovered funding need, million RUB.
2. Deficit exposure: sum of those stocks, million RUB × periods. This is not money saved.
3. Total principal drawn/repaid and terminal debt, million RUB.
4. An illustrative, uncalibrated logistic stress index. Its coefficients and synthetic PD inputs do not turn it into a default probability.

`make_results` computes all outcomes by replaying the supplied interventions. An empty or zero-principal intervention yields exactly the no-credit result. There is no multiplicative effect curve or preset superiority.

For seed 42, the borrower-score policy reduces deficit exposure by 14,522.24 million RUB × periods, versus 11,764.86 for the graph score, with 2,500.00 million RUB drawn and repaid by each. Peak late-horizon stress is unchanged after repayment. The different ordering of the uncalibrated logistic index is a reason to state the outcome metric, not a reason to claim a causal advantage.

## Evidence boundary

These are deterministic outputs conditional on one generated data set, two chosen heuristics and simplified zero-interest financing. They are not observed banking outcomes, estimates of treatment effects, empirical default probabilities or evidence that one credit product is better than another. More representative cash flows, multiple seeds, independent policies, real data and endogenous payment/production dynamics would be needed to evaluate those questions.
