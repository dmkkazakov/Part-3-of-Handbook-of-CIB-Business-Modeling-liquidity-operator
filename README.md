# Corporate Credit as a Liquidity Operator

Synthetic execution-liquidity graph dataset and reproducible code for an SSRN-style working paper.

## Thesis

Corporate credit is not just a product. It is a **temporal liquidity operator** that redistributes cash tension across firms, obligations and execution chains.

The repository provides a synthetic benchmark for testing this idea:

- firms as nodes;
- supply-chain and payment obligations as edges;
- cash tension as a dynamic state variable;
- financing as an intervention operator;
- bottleneck financing as a graph-aware allocation rule.

## Repository structure

```text
.
├── data/
│   ├── raw/
│   │   ├── firms.csv
│   │   ├── execution_edges.csv
│   │   ├── obligations.csv
│   │   ├── liquidity_timeseries.csv
│   │   ├── interventions.csv
│   │   └── simulation_results.csv
│   └── processed/
├── docs/
│   ├── DATA_DICTIONARY.md
│   └── METHOD_NOTE.md
├── figures/
├── src/
│   ├── generate_synthetic.py
│   ├── run_baselines.py
│   └── visualize.py
├── requirements.txt
├── CITATION.cff
└── LICENSE
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python src/generate_synthetic.py --firms 500 --edges 3200 --periods 26 --seed 42
python src/run_baselines.py
python src/visualize.py
```

## Dataset summary

Default generator creates:

- 500 synthetic firms;
- 3,200 supplier-buyer execution links;
- stochastic invoices and payment delays;
- 26 periods of liquidity states;
- bottleneck financing interventions;
- traditional vs execution-aware simulation curves.

## Main variables

### Cash tension

```text
T_i(t) = O_i(t) - C_i(t)
```

where `O_i(t)` is due obligations and `C_i(t)` is available liquidity.

### Bottleneck financing

```text
b* = argmax dR / dF_i
```

The practical interpretation: lend not automatically to the largest borrower, but to the node whose stabilization restores the largest execution capacity.

## Figures

After running `src/visualize.py`, the repository creates:

- `figures/cash_tension_propagation.png`
- `figures/collapse_probability_baseline.png`
- `figures/top_bottleneck_interventions.png`

## Important limitation

This is synthetic data. It is useful for reproducibility, method demonstration and publication packaging. It is not a real bank portfolio, not a credit decision engine and not a regulatory model.

## Citation

Use `CITATION.cff` or cite the repository as:

> Kazakov, D. (2026). Corporate Credit as a Liquidity Operator: Synthetic Execution-Liquidity Graph Dataset.

## License

MIT.
