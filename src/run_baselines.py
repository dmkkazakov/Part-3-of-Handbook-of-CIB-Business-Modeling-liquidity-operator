from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(exist_ok=True)

firms = pd.read_csv(DATA / "firms.csv")
ts = pd.read_csv(DATA / "liquidity_timeseries.csv")
edges = pd.read_csv(DATA / "execution_edges.csv")

stress = ts.groupby("firm_id", as_index=False).agg(
    total_tension_mrub=("cash_tension_mrub", "sum"),
    max_collapse_probability=("collapse_probability", "max"),
    avg_collapse_probability=("collapse_probability", "mean"),
)
exposure = edges.groupby("supplier_id", as_index=False)["annual_contract_mrub"].sum().rename(
    columns={"supplier_id": "firm_id", "annual_contract_mrub": "supplier_exposure_mrub"}
)

score = firms.merge(stress, on="firm_id", how="left").merge(exposure, on="firm_id", how="left").fillna(0)
score["borrower_centric_score"] = 0.65 * score["annual_revenue_mrub"].rank(pct=True) + 0.35 * (1 - score["pd_12m"].rank(pct=True))
score["liquidity_operator_score"] = (
    0.45 * score["total_tension_mrub"].rank(pct=True)
    + 0.35 * score["supplier_exposure_mrub"].rank(pct=True)
    + 0.20 * score["supplier_criticality"].rank(pct=True)
)
score.sort_values("liquidity_operator_score", ascending=False).to_csv(OUT / "firm_scores.csv", index=False)

summary = pd.DataFrame({
    "metric": ["mean_total_tension_top35_borrower", "mean_total_tension_top35_operator"],
    "value": [
        score.sort_values("borrower_centric_score", ascending=False).head(35)["total_tension_mrub"].mean(),
        score.sort_values("liquidity_operator_score", ascending=False).head(35)["total_tension_mrub"].mean(),
    ]
})
summary.to_csv(OUT / "baseline_summary.csv", index=False)
print("Saved baseline outputs to data/processed")
