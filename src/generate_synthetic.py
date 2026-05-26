"""
Generate a synthetic execution-liquidity graph for the paper:
Corporate Credit as a Liquidity Operator.

The data is synthetic by design. It imitates structural properties of CIB execution chains:
- anchor buyers and smaller suppliers;
- payment delays;
- receivable stress propagation;
- bottleneck nodes;
- alternative financing interventions.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import numpy as np
import pandas as pd


def sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-x))


def make_firms(n: int, rng: np.random.Generator) -> pd.DataFrame:
    sectors = np.array(["manufacturing", "construction", "logistics", "retail", "energy", "services"])
    size_class = rng.choice(["SME", "mid", "large", "anchor"], n, p=[0.42, 0.33, 0.18, 0.07])
    sector = rng.choice(sectors, n, p=[0.25, 0.18, 0.14, 0.16, 0.12, 0.15])

    base_revenue = {
        "SME": (80, 650),
        "mid": (650, 3500),
        "large": (3500, 22000),
        "anchor": (22000, 120000),
    }
    revenue = np.array([rng.uniform(*base_revenue[c]) for c in size_class])
    cash_buffer = revenue * rng.uniform(0.015, 0.085, n)
    pd_12m = np.clip(rng.beta(1.8, 32, n) + (size_class == "SME") * 0.025, 0.003, 0.35)
    supplier_criticality = np.clip(rng.normal(0.45, 0.22, n), 0, 1)

    return pd.DataFrame({
        "firm_id": [f"F{i:04d}" for i in range(n)],
        "sector": sector,
        "size_class": size_class,
        "annual_revenue_mrub": revenue.round(2),
        "initial_cash_buffer_mrub": cash_buffer.round(2),
        "pd_12m": pd_12m.round(4),
        "supplier_criticality": supplier_criticality.round(4),
    })


def make_edges(firms: pd.DataFrame, m: int, rng: np.random.Generator) -> pd.DataFrame:
    n = len(firms)
    ids = firms["firm_id"].to_numpy()
    size = firms["size_class"].to_numpy()
    revenue = firms["annual_revenue_mrub"].to_numpy()

    # Buyers are biased toward large/anchor firms; suppliers toward SME/mid firms.
    buyer_w = np.where(size == "anchor", 9.0, np.where(size == "large", 5.0, np.where(size == "mid", 2.0, 0.8)))
    supplier_w = np.where(size == "SME", 4.5, np.where(size == "mid", 3.0, np.where(size == "large", 1.5, 0.5)))
    buyer_w = buyer_w / buyer_w.sum()
    supplier_w = supplier_w / supplier_w.sum()

    pairs = set()
    rows = []
    attempts = 0
    while len(rows) < m and attempts < m * 20:
        attempts += 1
        buyer_idx = rng.choice(n, p=buyer_w)
        supplier_idx = rng.choice(n, p=supplier_w)
        if buyer_idx == supplier_idx:
            continue
        key = (ids[supplier_idx], ids[buyer_idx])
        if key in pairs:
            continue
        pairs.add(key)
        annual_contract = min(revenue[buyer_idx] * rng.uniform(0.001, 0.025), revenue[supplier_idx] * rng.uniform(0.01, 0.18))
        payment_term = int(rng.choice([15, 30, 45, 60, 75, 90], p=[0.10, 0.33, 0.24, 0.18, 0.08, 0.07]))
        delay_risk = np.clip(rng.beta(2, 10) + (payment_term >= 60) * 0.08, 0.01, 0.75)
        dependency = np.clip(rng.beta(2.2, 4.5), 0.02, 0.98)
        rows.append({
            "edge_id": f"E{len(rows):05d}",
            "supplier_id": ids[supplier_idx],
            "buyer_id": ids[buyer_idx],
            "annual_contract_mrub": round(float(annual_contract), 2),
            "payment_term_days": payment_term,
            "delay_risk": round(float(delay_risk), 4),
            "execution_dependency": round(float(dependency), 4),
        })
    return pd.DataFrame(rows)


def simulate(firms: pd.DataFrame, edges: pd.DataFrame, periods: int, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    firm_ids = firms["firm_id"].to_numpy()
    cash = firms.set_index("firm_id")["initial_cash_buffer_mrub"].astype(float).to_dict()
    revenue = firms.set_index("firm_id")["annual_revenue_mrub"].astype(float).to_dict()
    pd12 = firms.set_index("firm_id")["pd_12m"].astype(float).to_dict()

    obligations = []
    ts_rows = []

    incoming = {fid: np.zeros(periods + 8) for fid in firm_ids}
    outgoing = {fid: np.zeros(periods + 8) for fid in firm_ids}

    for _, e in edges.iterrows():
        monthly_amount = e.annual_contract_mrub / 12
        for t in range(periods):
            if rng.random() < 0.38:  # event occurs
                amount = max(0.05, rng.lognormal(math.log(max(monthly_amount, 0.1)), 0.42))
                due = t + max(1, int(round(e.payment_term_days / 30)))
                delayed = rng.random() < e.delay_risk
                actual_pay = due + (int(rng.choice([1, 2, 3], p=[0.65, 0.25, 0.10])) if delayed else 0)
                actual_pay = min(actual_pay, periods + 7)
                outgoing[e.buyer_id][actual_pay] += amount
                incoming[e.supplier_id][actual_pay] += amount
                obligations.append({
                    "period": t,
                    "edge_id": e.edge_id,
                    "supplier_id": e.supplier_id,
                    "buyer_id": e.buyer_id,
                    "invoice_amount_mrub": round(float(amount), 2),
                    "contractual_due_period": due,
                    "actual_payment_period": actual_pay,
                    "is_delayed": int(delayed),
                })

    for fid in firm_ids:
        c = cash[fid]
        for t in range(periods):
            operating_out = revenue[fid] / 12 * rng.uniform(0.045, 0.085)
            stochastic_shock = revenue[fid] / 12 * rng.normal(0, 0.018)
            obligations_t = max(0, outgoing[fid][t] + operating_out + stochastic_shock)
            inflow_t = incoming[fid][t]
            c = max(0, c + inflow_t - obligations_t)
            tension = max(0, obligations_t - (c + inflow_t))
            collapse_prob = float(sigmoid(-3.3 + 0.045 * tension + 7.0 * pd12[fid]))
            ts_rows.append({
                "firm_id": fid,
                "period": t,
                "cash_buffer_mrub": round(float(c), 2),
                "obligations_mrub": round(float(obligations_t), 2),
                "inflows_mrub": round(float(inflow_t), 2),
                "cash_tension_mrub": round(float(tension), 2),
                "collapse_probability": round(collapse_prob, 4),
            })

    return pd.DataFrame(obligations), pd.DataFrame(ts_rows), edges


def make_interventions(firms: pd.DataFrame, edges: pd.DataFrame, ts: pd.DataFrame, budget_mrub: float, k: int) -> pd.DataFrame:
    stress = ts.groupby("firm_id", as_index=False).agg(
        total_tension_mrub=("cash_tension_mrub", "sum"),
        max_collapse_probability=("collapse_probability", "max"),
    )
    out_degree = edges.groupby("supplier_id").size().rename("supplier_out_degree")
    in_degree = edges.groupby("buyer_id").size().rename("buyer_in_degree")
    exposure = edges.groupby("supplier_id")["annual_contract_mrub"].sum().rename("supplier_exposure_mrub")
    df = firms.merge(stress, on="firm_id", how="left") \
              .merge(out_degree, left_on="firm_id", right_index=True, how="left") \
              .merge(in_degree, left_on="firm_id", right_index=True, how="left") \
              .merge(exposure, left_on="firm_id", right_index=True, how="left")
    for col in ["supplier_out_degree", "buyer_in_degree", "supplier_exposure_mrub"]:
        df[col] = df[col].fillna(0)
    # Human-readable bottleneck score: not a magic oracle, just a useful controlled synthetic benchmark.
    df["bottleneck_score"] = (
        0.45 * df["total_tension_mrub"].rank(pct=True) +
        0.25 * df["supplier_exposure_mrub"].rank(pct=True) +
        0.20 * df["supplier_out_degree"].rank(pct=True) +
        0.10 * df["supplier_criticality"].rank(pct=True)
    )
    chosen = df.sort_values("bottleneck_score", ascending=False).head(k).copy()
    raw = chosen["bottleneck_score"] / chosen["bottleneck_score"].sum()
    chosen["intervention_amount_mrub"] = (raw * budget_mrub).round(2)
    chosen["operator_type"] = np.where(chosen["size_class"].isin(["SME", "mid"]), "factoring_or_revolver", "working_capital_line")
    return chosen[["firm_id", "operator_type", "intervention_amount_mrub", "bottleneck_score", "total_tension_mrub", "supplier_exposure_mrub", "supplier_out_degree"]]


def make_results(ts: pd.DataFrame, interventions: pd.DataFrame) -> pd.DataFrame:
    base = ts.groupby("period", as_index=False).agg(
        traditional_avg_collapse_probability=("collapse_probability", "mean"),
        traditional_total_tension_mrub=("cash_tension_mrub", "sum"),
    )
    # Synthetic effect curve: targeted interventions reduce propagation, but with diminishing returns.
    effect = 0.08 + 0.29 * (1 - np.exp(-np.linspace(0.2, 2.4, len(base))))
    base["execution_aware_avg_collapse_probability"] = (base["traditional_avg_collapse_probability"] * (1 - effect)).round(4)
    base["execution_aware_total_tension_mrub"] = (base["traditional_total_tension_mrub"] * (1 - effect * 0.78)).round(2)
    base["relative_collapse_reduction_pct"] = (
        100 * (1 - base["execution_aware_avg_collapse_probability"] / base["traditional_avg_collapse_probability"].replace(0, np.nan))
    ).round(2)
    return base


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--firms", type=int, default=500)
    parser.add_argument("--edges", type=int, default=3200)
    parser.add_argument("--periods", type=int, default=26)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="data/raw")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    firms = make_firms(args.firms, rng)
    edges = make_edges(firms, args.edges, rng)
    obligations, ts, edges = simulate(firms, edges, args.periods, rng)
    interventions = make_interventions(firms, edges, ts, budget_mrub=2500, k=35)
    results = make_results(ts, interventions)

    firms.to_csv(out / "firms.csv", index=False)
    edges.to_csv(out / "execution_edges.csv", index=False)
    obligations.to_csv(out / "obligations.csv", index=False)
    ts.to_csv(out / "liquidity_timeseries.csv", index=False)
    interventions.to_csv(out / "interventions.csv", index=False)
    results.to_csv(out / "simulation_results.csv", index=False)

    print(f"Saved synthetic liquidity-operator dataset to {out.resolve()}")


if __name__ == "__main__":
    main()
