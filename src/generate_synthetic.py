"""
Generate a synthetic execution-liquidity graph for the paper:
Corporate Credit as a Liquidity Operator.

The data is synthetic by design. It imitates structural properties of CIB execution chains:
- anchor buyers and smaller suppliers;
- payment delays;
- fixed invoice-payment schedules;
- heuristic graph-based recipient scores;
- alternative financing interventions.
"""
from __future__ import annotations

import argparse
import math
import json
from decimal import Decimal, ROUND_FLOOR
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
    return pd.DataFrame(rows, columns=["edge_id", "supplier_id", "buyer_id", "annual_contract_mrub", "payment_term_days", "delay_risk", "execution_dependency"])


def simulate(firms: pd.DataFrame, edges: pd.DataFrame, periods: int, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate fixed cash schedules, then calculate signed net liquidity.

    Scheduled transfers are paired between buyer and supplier, but are not
    conditioned on solvency. Negative liquidity is uncovered financing demand,
    not an authorised overdraft or evidence that a payment actually settled.
    """
    if not isinstance(periods, int) or periods < 1:
        raise ValueError("periods must be a positive integer")
    firm_ids = firms["firm_id"].to_numpy()
    cash = firms.set_index("firm_id")["initial_cash_buffer_mrub"].astype(float).to_dict()
    revenue = firms.set_index("firm_id")["annual_revenue_mrub"].astype(float).to_dict()
    pd12 = firms.set_index("firm_id")["pd_12m"].astype(float).to_dict()
    obligations, ts_rows = [], []
    incoming = {fid: np.zeros(periods + 8) for fid in firm_ids}
    outgoing = {fid: np.zeros(periods + 8) for fid in firm_ids}
    for _, e in edges.iterrows():
        monthly_amount = e.annual_contract_mrub / 12
        for t in range(periods):
            if rng.random() < 0.38:
                # Round once before adding the same amount to both schedules.
                amount = round(float(max(0.05, rng.lognormal(math.log(max(monthly_amount, 0.1)), 0.42))), 2)
                due = t + max(1, int(round(e.payment_term_days / 30)))
                delayed = rng.random() < e.delay_risk
                actual_pay = due + (int(rng.choice([1, 2, 3], p=[0.65, 0.25, 0.10])) if delayed else 0)
                outgoing[e.buyer_id][actual_pay] += amount
                incoming[e.supplier_id][actual_pay] += amount
                obligations.append({
                    "period": t, "edge_id": e.edge_id, "supplier_id": e.supplier_id,
                    "buyer_id": e.buyer_id, "invoice_amount_mrub": amount,
                    "contractual_due_period": due, "scheduled_payment_period": actual_pay,
                    "is_delayed": int(delayed),
                })
    for fid in firm_ids:
        c = cash[fid]
        for t in range(periods):
            operating_out = revenue[fid] / 12 * rng.uniform(0.045, 0.085)
            stochastic_shock = revenue[fid] / 12 * rng.normal(0, 0.018)
            operating_out = round(float(max(0, operating_out + stochastic_shock)), 2)
            outflow = round(float(outgoing[fid][t] + operating_out), 2)
            inflow = round(float(incoming[fid][t]), 2)
            opening = c
            c = round(opening + inflow - outflow, 2)
            tension = max(0.0, -c)
            ts_rows.append({
                "firm_id": fid, "period": t, "opening_cash_mrub": opening,
                "cash_buffer_mrub": c, "obligations_mrub": outflow,
                "inflows_mrub": inflow, "external_operating_outflow_mrub": operating_out,
                "cash_tension_mrub": tension, "pd_12m": pd12[fid],
                "synthetic_stress_index": float(sigmoid(-3.3 + 0.045 * tension + 7.0 * pd12[fid])),
            })
    return pd.DataFrame(obligations), pd.DataFrame(ts_rows), edges


def score_firms(firms: pd.DataFrame, edges: pd.DataFrame, ts: pd.DataFrame, decision_period: int) -> pd.DataFrame:
    """Use only observations strictly before the intervention decision."""
    if not isinstance(decision_period, int) or decision_period < 0:
        raise ValueError("decision_period must be a nonnegative integer")
    history = ts.loc[ts["period"] < decision_period]
    stress = history.groupby("firm_id", as_index=False).agg(
        historical_tension_exposure=("cash_tension_mrub", "sum"),
    )
    out_degree = edges.groupby("supplier_id").size().rename("supplier_out_degree")
    exposure = edges.groupby("supplier_id")["annual_contract_mrub"].sum().rename("supplier_exposure_mrub")
    df = firms.merge(stress, on="firm_id", how="left").merge(
        out_degree, left_on="firm_id", right_index=True, how="left").merge(
        exposure, left_on="firm_id", right_index=True, how="left")
    for col in ["historical_tension_exposure", "supplier_out_degree", "supplier_exposure_mrub"]:
        df[col] = df[col].fillna(0)
    df["graph_score"] = (
        0.45 * df["historical_tension_exposure"].rank(pct=True)
        + 0.25 * df["supplier_exposure_mrub"].rank(pct=True)
        + 0.20 * df["supplier_out_degree"].rank(pct=True)
        + 0.10 * df["supplier_criticality"].rank(pct=True)
    )
    df["borrower_centric_score"] = (
        0.65 * df["annual_revenue_mrub"].rank(pct=True)
        + 0.35 * (1 - df["pd_12m"].rank(pct=True))
    )
    df["decision_period"] = decision_period
    return df


def _allocate_cents(weights: pd.Series, budget_mrub: float) -> list[float]:
    """Largest-remainder allocation: never round above the stated budget."""
    if not math.isfinite(budget_mrub) or budget_mrub < 0:
        raise ValueError("budget_mrub must be finite and nonnegative")
    if len(weights) == 0:
        return []
    cents = int((Decimal(str(budget_mrub)) * 100).to_integral_value(rounding=ROUND_FLOOR))
    w = [Decimal(str(float(x))) for x in weights]
    total = sum(w)
    if total <= 0 or any(x < 0 for x in w):
        raise ValueError("allocation weights must be nonnegative with positive sum")
    exact = [Decimal(cents) * x / total for x in w]
    allocated = [int(x.to_integral_value(rounding=ROUND_FLOOR)) for x in exact]
    order = sorted(range(len(w)), key=lambda i: (-(exact[i] - allocated[i]), i))
    for i in order[:cents - sum(allocated)]:
        allocated[i] += 1
    return [x / 100 for x in allocated]


def make_interventions(firms: pd.DataFrame, edges: pd.DataFrame, ts: pd.DataFrame,
                       budget_mrub: float, k: int, *, decision_period: int = 13,
                       tenor_periods: int = 6, policy: str = "graph_score") -> pd.DataFrame:
    if not isinstance(k, int) or k < 0:
        raise ValueError("k must be a nonnegative integer")
    if not isinstance(tenor_periods, int) or tenor_periods < 1:
        raise ValueError("tenor_periods must be a positive integer")
    if policy not in {"graph_score", "borrower_centric"}:
        raise ValueError("unknown allocation policy")
    scores = score_firms(firms, edges, ts, decision_period)
    column = "graph_score" if policy == "graph_score" else "borrower_centric_score"
    chosen = scores.sort_values([column, "firm_id"], ascending=[False, True]).head(k).copy()
    chosen["intervention_amount_mrub"] = _allocate_cents(chosen[column], budget_mrub)
    chosen["policy"] = policy
    chosen["operator_type"] = "zero_interest_bullet_loan"
    chosen["start_period"] = decision_period
    chosen["tenor_periods"] = tenor_periods
    chosen["allocation_score"] = chosen[column]
    return chosen[["firm_id", "policy", "operator_type", "intervention_amount_mrub",
                   "start_period", "tenor_periods", "allocation_score",
                   "historical_tension_exposure", "supplier_exposure_mrub", "supplier_out_degree"]]


def replay_interventions(ts: pd.DataFrame, interventions: pd.DataFrame) -> pd.DataFrame:
    """Replay fixed cash schedules with finite, one-off, bullet-repaid loans.

    Each principal is drawn once at start and repaid at start + tenor. No
    interest or endogenous changes to counterparties' payments are assumed.
    """
    required = {"firm_id", "period", "opening_cash_mrub", "inflows_mrub", "obligations_mrub", "pd_12m"}
    if not required <= set(ts):
        raise ValueError("cash schedule is missing required columns")
    if ts.duplicated(["firm_id", "period"]).any():
        raise ValueError("duplicate firm-period observations")
    if ts.empty:
        raise ValueError("cash schedule must not be empty")
    for col in required - {"firm_id"}:
        if not np.isfinite(ts[col].to_numpy(dtype=float)).all():
            raise ValueError("cash schedule must contain finite numbers")
    draws, repayments = {}, {}
    bounds = ts.groupby("firm_id")["period"].agg(["min", "max"])
    if not interventions.empty:
        if not {"firm_id", "intervention_amount_mrub", "start_period", "tenor_periods"} <= set(interventions):
            raise ValueError("interventions are missing amount or timing")
        for row in interventions.itertuples(index=False):
            if row.firm_id not in bounds.index:
                raise ValueError("intervention references an unknown firm")
            amount = float(row.intervention_amount_mrub)
            if not math.isfinite(amount) or amount < 0:
                raise ValueError("principal must be finite and nonnegative")
            if not float(row.start_period).is_integer() or not float(row.tenor_periods).is_integer() or row.tenor_periods < 1:
                raise ValueError("start and tenor must be whole periods, with positive tenor")
            start, tenor = int(row.start_period), int(row.tenor_periods)
            first, last = bounds.loc[row.firm_id]
            if start < first:
                raise ValueError("pre-history loans require an explicit opening-debt model")
            if start <= last:
                key = (row.firm_id, start)
                draws[key] = draws.get(key, 0.0) + amount
                key = (row.firm_id, start + tenor)
                repayments[key] = repayments.get(key, 0.0) + amount
    rows = []
    for fid, group in ts.sort_values(["firm_id", "period"]).groupby("firm_id", sort=False):
        periods = group["period"].to_numpy()
        if not np.equal(periods, np.floor(periods)).all() or (len(periods) > 1 and not np.equal(np.diff(periods), 1).all()):
            raise ValueError("each firm's cash schedule must use consecutive integer periods")
        cash = float(group.iloc[0]["opening_cash_mrub"])
        debt = 0.0
        for source in group.to_dict("records"):
            t = int(source["period"])
            draw, repayment = draws.get((fid, t), 0.0), repayments.get((fid, t), 0.0)
            opening_cash, opening_debt = cash, debt
            cash = opening_cash + float(source["inflows_mrub"]) - float(source["obligations_mrub"]) + draw - repayment
            debt = opening_debt + draw - repayment
            if not math.isfinite(cash) or not math.isfinite(debt) or debt < -1e-8:
                raise ValueError("invalid cash or debt state")
            tension = max(0.0, -cash)
            source.update({
                "opening_cash_mrub": opening_cash, "cash_buffer_mrub": cash,
                "credit_draw_mrub": draw, "principal_repayment_mrub": repayment,
                "opening_debt_mrub": opening_debt, "closing_debt_mrub": max(0.0, debt),
                "cash_tension_mrub": tension,
                "synthetic_stress_index": float(sigmoid(-3.3 + 0.045 * tension + 7.0 * float(source["pd_12m"]))),
            })
            rows.append(source)
    return pd.DataFrame(rows)


def make_results(ts: pd.DataFrame, interventions: pd.DataFrame,
                 borrower_interventions: pd.DataFrame | None = None) -> pd.DataFrame:
    """Measured outcomes of the stated synthetic ledger, with no preset uplift."""
    policies = {"no_credit": pd.DataFrame()}
    if borrower_interventions is not None:
        policies["borrower_centric"] = borrower_interventions
    policies["graph_score"] = interventions
    result = None
    for name, loans in policies.items():
        replay = replay_interventions(ts, loans)
        aggregate = replay.groupby("period", as_index=False).agg(
            avg_stress_index=("synthetic_stress_index", "mean"),
            total_tension_mrub=("cash_tension_mrub", "sum"),
            credit_draw_mrub=("credit_draw_mrub", "sum"),
            principal_repayment_mrub=("principal_repayment_mrub", "sum"),
            closing_debt_mrub=("closing_debt_mrub", "sum"),
        ).rename(columns=lambda c: c if c == "period" else f"{name}_{c}")
        result = aggregate if result is None else result.merge(aggregate, on="period", validate="one_to_one")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--firms", type=int, default=500)
    parser.add_argument("--edges", type=int, default=3200)
    parser.add_argument("--periods", type=int, default=26)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--budget", type=float, default=2500.0)
    parser.add_argument("--targets", type=int, default=35)
    parser.add_argument("--decision-period", type=int)
    parser.add_argument("--tenor-periods", type=int, default=6)
    parser.add_argument("--out", type=str, default="data/raw")
    args = parser.parse_args()
    if args.firms < 2 or not 0 <= args.edges <= args.firms * (args.firms - 1) or args.periods < 2:
        parser.error("need at least two firms/periods and a feasible nonnegative edge count")
    decision = args.periods // 2 if args.decision_period is None else args.decision_period
    if not 0 <= decision < args.periods:
        parser.error("decision period must lie inside the simulation horizon")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    firms = make_firms(args.firms, rng)
    edges = make_edges(firms, args.edges, rng)
    obligations, ts, edges = simulate(firms, edges, args.periods, rng)
    kwargs = dict(budget_mrub=args.budget, k=args.targets, decision_period=decision, tenor_periods=args.tenor_periods)
    interventions = make_interventions(firms, edges, ts, **kwargs)
    borrower = make_interventions(firms, edges, ts, policy="borrower_centric", **kwargs)
    results = make_results(ts, interventions, borrower)
    for name, frame in {
        "firms": firms, "execution_edges": edges, "obligations": obligations,
        "liquidity_timeseries": ts, "interventions": interventions,
        "borrower_interventions": borrower, "simulation_results": results,
        "liquidity_graph_score": replay_interventions(ts, interventions),
        "liquidity_borrower_centric": replay_interventions(ts, borrower),
    }.items():
        frame.to_csv(out / f"{name}.csv", index=False, float_format="%.10g")
    (out / "experiment_metadata.json").write_text(json.dumps({
        "seed": args.seed, "firms": len(firms), "edges": len(edges), "periods": args.periods,
        "decision_period": decision, "tenor_periods": args.tenor_periods,
        "budget_mrub_per_funded_policy": args.budget, "targets_per_policy": args.targets,
        "synthetic": True, "graph_payment_feedback": False,
        "interest_rate": 0.0, "calibrated_default_probability": False,
    }, indent=2) + "\n")
    print(f"Saved paired synthetic ledger calculations to {out.resolve()}")


if __name__ == "__main__":
    main()
