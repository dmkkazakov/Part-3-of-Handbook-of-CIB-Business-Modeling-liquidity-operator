from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
res = pd.read_csv(DATA / "simulation_results.csv")
inter = pd.read_csv(DATA / "interventions.csv")
labels = {"no_credit": "No credit", "borrower_centric": "Borrower score: equal budget", "graph_score": "Graph score: equal budget"}
fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
for policy, label in labels.items():
    axes[0].plot(res["period"], res[f"{policy}_total_tension_mrub"], label=label)
axes[0].set_title("Synthetic cash deficits on fixed payment schedules")
axes[0].set_ylabel("Uncovered liquidity, million RUB")
axes[0].legend()
for policy, color in [("borrower_centric", "tab:orange"), ("graph_score", "tab:green")]:
    reduction = res["no_credit_total_tension_mrub"] - res[f"{policy}_total_tension_mrub"]
    axes[1].plot(res["period"], reduction, color=color, label=labels[policy])
axes[1].set_title("Reduction versus no credit; relief ends after principal repayment", fontsize=10)
axes[1].set_xlabel("Monthly period (0-based)")
axes[1].set_ylabel("Reduction, million RUB")
axes[1].set_ylim(bottom=0)
axes[1].grid(alpha=0.2)
fig.tight_layout()
fig.savefig(FIG / "cash_tension_propagation.png", dpi=180)
plt.close(fig)

plt.figure(figsize=(8, 5))
plt.bar(["No credit", "Borrower score", "Graph score"],
        [res[f"{p}_avg_stress_index"].mean() for p in labels])
plt.title("Synthetic stress index (not a default probability)")
plt.ylabel("Mean uncalibrated index")
plt.tight_layout()
# Historical filename retained; the corrected chart explicitly labels the index.
plt.savefig(FIG / "collapse_probability_baseline.png", dpi=180)
plt.close()

fig, ax = plt.subplots(figsize=(9, 5))
selected = inter.sort_values("intervention_amount_mrub", ascending=False).head(20)
ax.bar(selected["firm_id"], selected["intervention_amount_mrub"])
ax.set_title("Top-20 principal allocations from the graph-score policy")
ax.set_xlabel("Firm")
ax.set_ylabel("One-off principal, million RUB")
ax.tick_params(axis="x", rotation=60)
fig.tight_layout()
fig.savefig(FIG / "top_bottleneck_interventions.png", dpi=180)
plt.close(fig)
print(f"Saved corrected synthetic figures to {FIG}")
