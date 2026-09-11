"""Re-optimize Q3 under the alternative net-replacement settlement interpretation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "optimizer_source"))
from microgrid_models import StorageParams  # noqa: E402
from run_pipeline import read_inputs, simulate_mpc  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--output-root", type=Path, required=True)
    args = ap.parse_args()
    ts, fc, margins, scenarios, official, q1 = read_inputs(args.data_root)
    alt, alt_daily = simulate_mpc(ts, fc, official, "alternative_net_settlement", StorageParams(),
                                  dynamic=False, down=-0.5, up=1.5)
    price = alt["price_actual"].to_numpy(float)
    diff = alt["purchase_adjust_kwh"].to_numpy(float) - alt["purchase_plan_kwh"].to_numpy(float)
    alt["alt_cost"] = (price*alt["purchase_plan_kwh"].to_numpy(float)
                       + np.where(diff >= 0, 1.5*price*diff, -0.5*price*(-diff))
                       + 5.0*price*alt["purchase_emergency_kwh"].to_numpy(float))
    main_daily = pd.read_csv(args.output_root / "daily_metrics.csv")
    main_daily = main_daily[main_daily.strategy_name == "result3"].set_index("date")
    key_dates = ["2025-03-20", "2025-06-01", "2025-06-21", "2025-09-23", "2025-12-21"]
    rows = []
    for date in key_dates:
        a = alt[alt.date == date]
        m = main_daily.loc[date]
        for setting, cost, adjusted, downs in [
            ("additive_penalty_main", float(m.cost_yuan), np.nan, np.nan),
            ("net_replacement_alternative", float(a.alt_cost.sum()), float(a.purchase_adjust_kwh.sum()),
             int((a.purchase_adjust_kwh < a.purchase_plan_kwh-1e-7).sum())),
        ]:
            rows.append({"scope": "Q3_key_dates", "parameter": "settlement_interpretation",
                         "setting": setting, "date": date, "cost_yuan": cost,
                         "planned_kwh": float(a.purchase_plan_kwh.sum()), "objective": np.nan,
                         "solve_time_s": float(alt_daily[alt_daily.date == date].solve_time_s.iloc[0]),
                         "adjusted_kwh": adjusted, "down_adjustment_intervals": downs})
    sens_path = args.output_root / "sensitivity_results.csv"
    sens = pd.read_csv(sens_path)
    sens = sens[~((sens["scope"] == "Q3_key_dates") & (sens["parameter"] == "settlement_interpretation"))]
    pd.concat([sens, pd.DataFrame(rows)], ignore_index=True).to_csv(
        sens_path, index=False, encoding="utf-8-sig", float_format="%.8f"
    )


if __name__ == "__main__":
    main()
