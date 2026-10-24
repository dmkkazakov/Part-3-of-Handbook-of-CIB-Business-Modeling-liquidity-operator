"""Summarise paired outcomes; do not infer effectiveness from target scores."""
import json
from pathlib import Path
import pandas as pd
from generate_synthetic import score_firms

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(exist_ok=True)
firms = pd.read_csv(DATA / "firms.csv")
ts = pd.read_csv(DATA / "liquidity_timeseries.csv")
edges = pd.read_csv(DATA / "execution_edges.csv")
metadata = json.loads((DATA / "experiment_metadata.json").read_text())
scores = score_firms(firms, edges, ts, int(metadata["decision_period"]))
scores.sort_values("graph_score", ascending=False).to_csv(OUT / "firm_scores.csv", index=False)
results = pd.read_csv(DATA / "simulation_results.csv")
rows = []
for policy in ["no_credit", "borrower_centric", "graph_score"]:
    rows.append({
        "policy": policy,
        "principal_drawn_mrub": results[f"{policy}_credit_draw_mrub"].sum(),
        "principal_repaid_mrub": results[f"{policy}_principal_repayment_mrub"].sum(),
        "terminal_debt_mrub": results[f"{policy}_closing_debt_mrub"].iloc[-1],
        "tension_exposure_mrub_periods": results[f"{policy}_total_tension_mrub"].sum(),
        "peak_system_tension_mrub": results[f"{policy}_total_tension_mrub"].max(),
        "mean_uncalibrated_stress_index": results[f"{policy}_avg_stress_index"].mean(),
    })
summary = pd.DataFrame(rows)
reference = summary.loc[summary["policy"] == "no_credit", "tension_exposure_mrub_periods"].iloc[0]
summary["tension_exposure_reduction_mrub_periods"] = reference - summary["tension_exposure_mrub_periods"]
summary.to_csv(OUT / "baseline_summary.csv", index=False)
print(summary.to_string(index=False))
