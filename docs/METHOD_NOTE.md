# Method Note

This repository supports the paper concept **Corporate Credit as a Liquidity Operator**.

## Core idea

Corporate credit is modeled as a temporal operator acting on a liquidity state:

`X(t+1) = L(X(t), G, F, theta)`

where:

- `X(t)` is the liquidity state of firms;
- `G` is the execution graph;
- `F` is the funding intervention;
- `theta` contains product parameters such as tenor, repayment profile, collateral and covenants.

## Cash tension

`T_i(t) = O_i(t) - C_i(t)`

where:

- `O_i(t)` = obligations due at time `t`;
- `C_i(t)` = available liquidity buffer and inflows;
- `T_i(t) > 0` means a cash deficit.

## Bottleneck financing

The intervention target is not necessarily the largest borrower. The target is the node where marginal funding restores the largest part of the execution graph.

In simple benchmark form:

`b* = argmax dR / dF_i`

The repository uses a transparent bottleneck score based on:

- accumulated cash tension;
- supplier exposure;
- supplier out-degree;
- criticality.

This is deliberately simple. It is a baseline, not a claim that banks should run production credit systems on four columns and a prayer.

## Why synthetic data

Real corporate banking data is sensitive: payments, contracts, limits, invoices, defaults and group structures are usually confidential.
Synthetic data allows reproducible publication without disclosing client information.
