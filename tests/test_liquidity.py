import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from generate_synthetic import (simulate, make_firms, make_edges, make_interventions,
                                replay_interventions, make_results, _allocate_cents)


def schedule(periods=6):
    rows = []
    for fid, initial in [("A", 100.0), ("B", 1000.0)]:
        cash = initial
        for period in range(periods):
            opening = cash
            cash -= 60.0
            rows.append(dict(firm_id=fid, period=period, opening_cash_mrub=opening,
                             cash_buffer_mrub=cash, inflows_mrub=0.0, obligations_mrub=60.0,
                             pd_12m=0.05, cash_tension_mrub=max(0, -cash)))
    return pd.DataFrame(rows)


def loan(amount=100.0, start=1, tenor=2, fid="A"):
    return pd.DataFrame([dict(firm_id=fid, intervention_amount_mrub=amount,
                              start_period=start, tenor_periods=tenor)])


class LiquidityTests(unittest.TestCase):
    def test_opening_cash_is_not_counted_twice(self):
        out = replay_interventions(schedule(), pd.DataFrame())
        a = out[out.firm_id == "A"]
        self.assertEqual(a.iloc[0].cash_buffer_mrub, 40)
        self.assertEqual(a.iloc[0].cash_tension_mrub, 0)
        self.assertEqual(a.iloc[1].cash_tension_mrub, 20)
        self.assertEqual(a.iloc[2].cash_tension_mrub, 80)

    def test_zero_intervention_has_zero_effect(self):
        results = make_results(schedule(), loan(amount=0), loan(amount=0))
        for metric in ["total_tension_mrub", "avg_stress_index"]:
            np.testing.assert_array_equal(results[f"no_credit_{metric}"], results[f"graph_score_{metric}"])
            np.testing.assert_array_equal(results[f"no_credit_{metric}"], results[f"borrower_centric_{metric}"])

    def test_omitted_borrower_policy_is_not_mislabeled(self):
        results = make_results(schedule(), loan())
        self.assertFalse(any(c.startswith("borrower_centric_") for c in results.columns))
        self.assertIn("no_credit_total_tension_mrub", results)
        self.assertIn("graph_score_total_tension_mrub", results)

    def test_actual_recipient_changes_result(self):
        result_a = make_results(schedule(), loan(fid="A"))
        result_b = make_results(schedule(), loan(fid="B"))
        self.assertLess(result_a.graph_score_total_tension_mrub.sum(), result_b.graph_score_total_tension_mrub.sum())

    def test_cash_debt_conservation_and_maturity(self):
        out = replay_interventions(schedule(), loan())
        np.testing.assert_allclose(out.cash_buffer_mrub,
            out.opening_cash_mrub + out.inflows_mrub - out.obligations_mrub + out.credit_draw_mrub - out.principal_repayment_mrub)
        np.testing.assert_allclose(out.closing_debt_mrub,
            out.opening_debt_mrub + out.credit_draw_mrub - out.principal_repayment_mrub)
        a = out[out.firm_id == "A"].set_index("period")
        self.assertEqual(a.loc[0, "credit_draw_mrub"], 0)
        self.assertEqual(a.loc[1, "credit_draw_mrub"], 100)
        self.assertEqual(a.loc[2, "principal_repayment_mrub"], 0)
        self.assertEqual(a.loc[3, "principal_repayment_mrub"], 100)
        self.assertEqual(out.credit_draw_mrub.sum(), 100)
        self.assertEqual(out.principal_repayment_mrub.sum(), 100)
        base = replay_interventions(schedule(), pd.DataFrame())
        np.testing.assert_allclose(out.loc[out.period >= 3, "cash_buffer_mrub"], base.loc[base.period >= 3, "cash_buffer_mrub"])

    def test_outside_window_does_not_draw(self):
        out = replay_interventions(schedule(), loan(start=8))
        self.assertEqual(out.credit_draw_mrub.sum(), 0)
        self.assertEqual(out.principal_repayment_mrub.sum(), 0)

    def test_budget_rounding_never_overspends(self):
        for budget in [0, 0.01, 1.0, 1.009, 2500.0]:
            amounts = _allocate_cents(pd.Series([1.0, 1.0, 1.0]), budget)
            self.assertLessEqual(sum(amounts), budget + 1e-10)
            self.assertAlmostEqual(sum(amounts), int(budget * 100 + 1e-9) / 100)

    def test_same_budget_and_no_future_information(self):
        rng = np.random.default_rng(42)
        firms = make_firms(8, rng)
        edges = make_edges(firms, 16, rng)
        _, ts, _ = simulate(firms, edges, 8, rng)
        kwargs = dict(budget_mrub=100.0, k=3, decision_period=4, tenor_periods=2)
        graph = make_interventions(firms, edges, ts, **kwargs)
        borrower = make_interventions(firms, edges, ts, policy="borrower_centric", **kwargs)
        self.assertAlmostEqual(graph.intervention_amount_mrub.sum(), 100)
        self.assertAlmostEqual(borrower.intervention_amount_mrub.sum(), 100)
        changed = ts.copy()
        changed.loc[changed.period >= 4, "cash_tension_mrub"] = 1e9
        pd.testing.assert_frame_equal(graph, make_interventions(firms, edges, changed, **kwargs))

    def test_generated_internal_transfers_balance(self):
        rng = np.random.default_rng(7)
        firms = make_firms(6, rng)
        edges = make_edges(firms, 20, rng)
        _, ts, _ = simulate(firms, edges, 10, rng)
        grouped = ts.groupby("period")
        np.testing.assert_allclose(grouped.inflows_mrub.sum(),
            grouped.obligations_mrub.sum() - grouped.external_operating_outflow_mrub.sum(), atol=1e-8)
        np.testing.assert_allclose(ts.cash_buffer_mrub, ts.opening_cash_mrub + ts.inflows_mrub - ts.obligations_mrub, atol=1e-8)

    def test_invalid_inputs_rejected(self):
        for invalid in [loan(amount=-1), loan(tenor=0), loan(fid="unknown")]:
            with self.assertRaises(ValueError):
                replay_interventions(schedule(), invalid)
        with self.assertRaises(ValueError):
            replay_interventions(pd.concat([schedule(), schedule().iloc[:1]]), loan())


if __name__ == "__main__":
    unittest.main()
