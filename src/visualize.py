from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

res = pd.read_csv(DATA / "simulation_results.csv")
inter = pd.read_csv(DATA / "interventions.csv")
ts = pd.read_csv(DATA / "liquidity_timeseries.csv")

plt.figure(figsize=(9, 5))
plt.plot(res["period"], res["traditional_total_tension_mrub"], label="Traditional allocation")
plt.plot(res["period"], res["execution_aware_total_tension_mrub"], label="Execution-aware intervention")
plt.title("Cash tension propagation: traditional vs execution-aware lending")
plt.xlabel("Period")
plt.ylabel("Total cash tension, MRUB")
plt.legend()
plt.tight_layout()
plt.savefig(FIG / "cash_tension_propagation.png", dpi=180)
plt.close()

plt.figure(figsize=(7, 5))
avg = [res["traditional_avg_collapse_probability"].mean(), res["execution_aware_avg_collapse_probability"].mean()]
plt.bar(["Traditional", "Execution-aware"], avg)
plt.title("Average execution collapse probability")
plt.ylabel("Probability")
plt.tight_layout()
plt.savefig(FIG / "collapse_probability_baseline.png", dpi=180)
plt.close()

plt.figure(figsize=(8, 5))
inter.sort_values("intervention_amount_mrub", ascending=False).head(20).plot(
    x="firm_id", y="intervention_amount_mrub", kind="bar", legend=False
)
plt.title("Top-20 bottleneck financing interventions")
plt.xlabel("Firm")
plt.ylabel("Intervention amount, MRUB")
plt.tight_layout()
plt.savefig(FIG / "top_bottleneck_interventions.png", dpi=180)
plt.close()

print(f"Saved figures to {FIG}")
