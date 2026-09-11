"""End-to-end solver and causal simulator for CUMCM 2026 Problem C.

Usage:
  python run_pipeline.py --data-root <directory containing processed_timeseries.csv>
                         --output-root <delivery directory>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "optimizer_source"))
from microgrid_models import (  # noqa: E402
    StorageParams,
    adjustment_dispatch,
    causal_execute,
    deterministic_dispatch,
    stochastic_cvar_plan,
)

SEED = 20260910
DT_H = 1.0 / 6.0
DATES = pd.date_range("2025-02-01", "2025-12-31", freq="D")
UPDATES = (0, 36, 72, 108)


def read_inputs(root: Path):
    ts = pd.read_csv(root / "processed_timeseries.csv", parse_dates=["date"]).sort_values(["date", "interval_index"])
    fc = pd.read_csv(root / "forecast_results.csv", parse_dates=["date"]).sort_values(["date", "interval_index"])
    margins = pd.read_csv(root / "scenario_data" / "residual_quantile_margins.csv.gz", parse_dates=["target_date"])
    scenarios = pd.read_csv(root / "scenario_data" / "joint_scenarios.csv.gz", parse_dates=["target_date"])
    official = pd.read_csv(root / "scenario_data" / "official_forecasts_long.csv.gz", parse_dates=["issue_date", "date"])
    q1 = pd.read_excel(root / "source_inputs" / "附件1.xlsx", header=0)
    return ts, fc, margins, scenarios, official, q1


def soc_start_from_end(soc0, end):
    return np.r_[float(soc0), np.asarray(end[:-1], dtype=float)]


def validation_stats(load, pv, purchase, emergency, charge, discharge, curtail, soc_start, soc_end, params):
    balance = purchase + emergency + pv + discharge - load - charge - curtail
    soc_eq = soc_start + params.eta_charge*charge - discharge/params.eta_discharge - soc_end
    return {
        "max_energy_balance_residual_kwh": float(np.max(np.abs(balance))),
        "max_soc_residual_kwh": float(np.max(np.abs(soc_eq))),
        "soc_min_kwh": float(np.min(np.r_[soc_start, soc_end])),
        "soc_max_kwh": float(np.max(np.r_[soc_start, soc_end])),
        "max_charge_kwh": float(np.max(charge)),
        "max_discharge_kwh": float(np.max(discharge)),
        "simultaneous_charge_discharge_intervals": int(np.sum((charge > 1e-7) & (discharge > 1e-7))),
    }


def solution_frame(base, strategy, plan, adjust, execution, price_settle, price_forecast,
                   load_forecast, pv_forecast, status, solve_time, params):
    g = base.sort_values("interval_index").reset_index(drop=True)
    load = g["load_actual_kw"].to_numpy(float) * DT_H
    pv = g["pv_actual_kw"].to_numpy(float) * DT_H
    plan = np.asarray(plan, float); adjust = np.asarray(adjust, float)
    emergency = execution["emergency"]
    final = (adjust if strategy in {"result3", "result4-3"} else plan) + emergency
    cost_plan = np.asarray(price_settle) * plan
    if strategy in {"result3", "result4-3"}:
        diff = adjust - plan
        cost_adjust = np.where(diff >= 0, 1.5*np.asarray(price_settle)*diff, 0.5*np.asarray(price_settle)*(-diff))
    else:
        cost_adjust = np.zeros(len(g))
    cost_emergency = 5.0*np.asarray(price_settle)*emergency
    stats = validation_stats(load, pv, final-emergency, emergency, execution["charge"], execution["discharge"],
                             execution["curtailment"], execution["soc_start"], execution["soc_end"], params)
    out = pd.DataFrame({
        "date": g["date"].dt.strftime("%Y-%m-%d"),
        "interval_index": g["interval_index"].astype(int),
        "output_interval_label": g["output_interval_label"].astype(str),
        "load_actual_kw": g["load_actual_kw"].to_numpy(float),
        "pv_actual_kw": g["pv_actual_kw"].to_numpy(float),
        "load_forecast_kw": np.asarray(load_forecast, float),
        "pv_forecast_kw": np.asarray(pv_forecast, float),
        "price_actual": np.asarray(price_settle, float),
        "price_forecast": np.asarray(price_forecast, float),
        "purchase_plan_kwh": plan,
        "purchase_adjust_kwh": adjust,
        "purchase_final_kwh": final,
        "purchase_emergency_kwh": emergency,
        "charge_kwh": execution["charge"],
        "discharge_kwh": execution["discharge"],
        "soc_start_kwh": execution["soc_start"],
        "soc_end_kwh": execution["soc_end"],
        "curtailment_kwh": execution["curtailment"],
        "cost_plan": cost_plan,
        "cost_adjust": cost_adjust,
        "cost_emergency": cost_emergency,
        "cost_total": cost_plan + cost_adjust + cost_emergency,
        "strategy_name": strategy,
        "scenario_seed": SEED,
        "solver_status": status,
    })
    metric = daily_metric(out, solve_time, stats)
    return out, metric


def daily_metric(df, solve_time, stats):
    return {
        "strategy_name": str(df["strategy_name"].iloc[0]),
        "date": str(df["date"].iloc[0]),
        "cost_yuan": float(df["cost_total"].sum()),
        "plan_cost_yuan": float(df["cost_plan"].sum()),
        "adjust_cost_yuan": float(df["cost_adjust"].sum()),
        "emergency_cost_yuan": float(df["cost_emergency"].sum()),
        "planned_purchase_kwh": float(df["purchase_plan_kwh"].sum()),
        "final_purchase_kwh": float(df["purchase_final_kwh"].sum()),
        "emergency_purchase_kwh": float(df["purchase_emergency_kwh"].sum()),
        "storage_throughput_kwh": float((df["charge_kwh"] + df["discharge_kwh"]).sum()),
        "curtailment_kwh": float(df["curtailment_kwh"].sum()),
        "soc_start_kwh": float(df["soc_start_kwh"].iloc[0]),
        "soc_end_kwh": float(df["soc_end_kwh"].iloc[-1]),
        "solve_time_s": float(solve_time),
        "solver_status": str(df["solver_status"].iloc[0]),
        **stats,
    }


def q1_outputs(q1, params):
    price = pd.to_numeric(q1.iloc[:, 1]).to_numpy(float)
    load_kw = pd.to_numeric(q1.iloc[:, 2]).to_numpy(float)
    pv_kw = pd.to_numeric(q1.iloc[:, 3]).to_numpy(float)
    net = (load_kw-pv_kw)*DT_H
    opt = deterministic_dispatch(net, price, 6000.0, params, terminal_soc_kwh=6000.0)
    execution = {"charge": opt.charge, "discharge": opt.discharge, "emergency": np.zeros(144),
                 "curtailment": opt.curtailment, "soc_end": opt.soc_end,
                 "soc_start": soc_start_from_end(6000.0, opt.soc_end)}
    labels = [f"{(10*i)//60%24}:{(10*i)%60:02d}-{(10*(i+1))//60%24}:{(10*(i+1))%60:02d}" for i in range(1,145)]
    # Official labels are supplied by the unified table and are position-bound.
    base = pd.DataFrame({"date": pd.Timestamp("2025-01-01"), "interval_index": np.arange(1,145),
                         "output_interval_label": labels, "load_actual_kw": load_kw, "pv_actual_kw": pv_kw})
    # Correct the labels to the official mapping via the caller after creation.
    return base, price, load_kw, pv_kw, opt, execution


def selected_scenarios(jday, scenario_count):
    ids = np.array(sorted(jday["scenario_id"].unique()), dtype=int)
    pick = ids[np.unique(np.linspace(0, len(ids)-1, scenario_count).round().astype(int))]
    d = jday[jday["scenario_id"].isin(pick)].sort_values(["scenario_id", "interval_index"])
    S = len(pick)
    return d, S


def plan_for_day(mode, fday, mday, jday, price_forecast, soc, params, scenario_count=8,
                 alpha=.90, risk_weight=.20, emergency_multiplier=5.0, dynamic=False):
    load_f = fday["load_pred_selected_kw"].to_numpy(float)
    pv_f = fday["pv_pred_selected_kw"].to_numpy(float)
    if mode == "point":
        return deterministic_dispatch((load_f-pv_f)*DT_H, price_forecast, soc, params, terminal_soc_kwh=soc)
    if mode == "safety":
        margin = np.maximum(0.0, mday.sort_values("interval_index")["net_load_q90"].to_numpy(float))
        return deterministic_dispatch((load_f-pv_f+margin)*DT_H, price_forecast, soc, params, terminal_soc_kwh=soc)
    if mode == "fixed_rule":
        net = (load_f-pv_f)*DT_H
        lo, hi = np.quantile(price_forecast, [.25, .75])
        return deterministic_dispatch(net, price_forecast, soc, params, terminal_soc_kwh=soc,
                                      charge_allowed=(price_forecast <= lo) | (net < 0),
                                      discharge_allowed=price_forecast >= hi)
    if mode == "cvar":
        js, S = selected_scenarios(jday, scenario_count)
        lr = js["load_residual_kw"].to_numpy(float).reshape(S, 144)
        pr = js["pv_residual_kw"].to_numpy(float).reshape(S, 144)
        load_s = np.maximum(0.0, load_f[None, :] + lr) * DT_H
        pv_s = np.maximum(0.0, pv_f[None, :] + pr) * DT_H
        if dynamic:
            er = js["price_residual"].to_numpy(float).reshape(S, 144)
            ps = np.maximum(0.001, price_forecast[None, :] + er)
        else:
            ps = np.tile(price_forecast, (S, 1))
        return stochastic_cvar_plan(load_s, pv_s, ps, soc, params, emergency_multiplier,
                                    alpha, risk_weight, terminal_soc_kwh=soc)
    raise ValueError(mode)


def simulate_q2(ts, fc, margins, scenarios, mode, strategy, params, dynamic=False,
                collect=True, scenario_count=8, alpha=.90, risk_weight=.20, emergency_multiplier=5.0):
    rows, metrics = [], []
    soc = 6000.0
    ts_by = {d: g.sort_values("interval_index") for d, g in ts[ts.date.isin(DATES)].groupby("date")}
    fc_by = {d: g.sort_values("interval_index") for d, g in fc[fc.date.isin(DATES)].groupby("date")}
    m_by = {d: g.sort_values("interval_index") for d, g in margins.groupby("target_date")}
    j_by = {d: g for d, g in scenarios.groupby("target_date")}
    previous_price = None
    for ix, date in enumerate(DATES):
        g = ts_by[date]; f = fc_by[date]; m = m_by[date]; j = j_by[date]
        actual_price = g["price_actual"].to_numpy(float) if dynamic else g["price_static"].to_numpy(float)
        if dynamic:
            if previous_price is None:
                prev = ts[ts.date == date-pd.Timedelta(days=1)].sort_values("interval_index")
                previous_price = prev["price_actual"].to_numpy(float)
            price_f = previous_price.copy()
        else:
            price_f = g["price_static"].to_numpy(float)
        started = perf_counter()
        if mode == "no_storage":
            plan = np.maximum(0.0, (f["load_pred_selected_kw"].to_numpy(float)-f["pv_pred_selected_kw"].to_numpy(float))*DT_H)
            load_a = g["load_actual_kw"].to_numpy(float)*DT_H; pv_a = g["pv_actual_kw"].to_numpy(float)*DT_H
            deficit = load_a-pv_a-plan
            ex = {"charge": np.zeros(144), "discharge": np.zeros(144), "emergency": np.maximum(deficit,0),
                  "curtailment": np.maximum(-deficit,0), "soc_start": np.full(144,soc), "soc_end": np.full(144,soc)}
            solve_time = perf_counter()-started; status = "CAUSAL_BASELINE"
        else:
            sol = plan_for_day(mode, f, m, j, price_f, soc, params, scenario_count, alpha,
                               risk_weight, emergency_multiplier, dynamic)
            plan = sol.purchase
            ex = causal_execute(plan, g["load_actual_kw"].to_numpy(float)*DT_H,
                                g["pv_actual_kw"].to_numpy(float)*DT_H, soc, params)
            solve_time = sol.solve_time_s; status = f"OPTIMAL_{mode.upper()}"
        frame, metric = solution_frame(g, strategy, plan, plan, ex, actual_price, price_f,
                                       f["load_pred_selected_kw"].to_numpy(float),
                                       f["pv_pred_selected_kw"].to_numpy(float), status, solve_time, params)
        soc = float(ex["soc_end"][-1])
        previous_price = g["price_actual"].to_numpy(float)
        if collect: rows.append(frame)
        metric["model_variant"] = mode
        metric["dynamic_price"] = dynamic
        metrics.append(metric)
    return (pd.concat(rows, ignore_index=True) if rows else None), pd.DataFrame(metrics)


def latest_pv_forecast(official, date, issue_hour, base_pv):
    g = official[(official.issue_date == date) & (official.issue_hour == issue_hour) & (official.date == date)]
    out = np.asarray(base_pv, float).copy()
    if not g.empty:
        idx = g["interval_index"].astype(int).to_numpy()-1
        out[idx] = g["pv_forecast_kw"].to_numpy(float)
    return out


def simulate_mpc(ts, fc, official, strategy, params, dynamic=False, down=.5, up=1.5):
    rows, metrics = [], []
    soc = 6000.0
    ts_by = {d: g.sort_values("interval_index") for d, g in ts[ts.date.isin(DATES)].groupby("date")}
    fc_by = {d: g.sort_values("interval_index") for d, g in fc[fc.date.isin(DATES)].groupby("date")}
    for date in DATES:
        g = ts_by[date]; f = fc_by[date]
        load_a_kw = g["load_actual_kw"].to_numpy(float); pv_a_kw = g["pv_actual_kw"].to_numpy(float)
        load_base = f["load_pred_selected_kw"].to_numpy(float); pv_base = f["pv_pred_selected_kw"].to_numpy(float)
        settle_price = g["price_actual"].to_numpy(float) if dynamic else g["price_static"].to_numpy(float)
        if dynamic:
            prev = ts[ts.date == date-pd.Timedelta(days=1)].sort_values("interval_index")
            price_base = prev["price_actual"].to_numpy(float)
        else:
            price_base = g["price_static"].to_numpy(float)
        initial = deterministic_dispatch((load_base-pv_base)*DT_H, price_base, soc, params, terminal_soc_kwh=6000.0)
        plan = initial.purchase.copy(); adjust = plan.copy()
        used_load_f = load_base.copy(); used_pv_f = pv_base.copy(); used_price_f = price_base.copy()
        arrays = {k: np.zeros(144) for k in ["charge","discharge","emergency","curtailment","soc_start","soc_end"]}
        solve_time = initial.solve_time_s
        current_soc = soc
        for seg, start in enumerate(UPDATES):
            stop = UPDATES[seg+1] if seg+1 < len(UPDATES) else 144
            hour = start//6
            lf = load_base.copy()
            pf = latest_pv_forecast(official, date, hour, pv_base)
            prf = price_base.copy()
            if start:
                hist0 = max(0, start-12)
                load_bias = float(np.mean(load_a_kw[hist0:start]-load_base[hist0:start]))
                lf[start:] = np.maximum(0.0, load_base[start:]+load_bias)
                if dynamic:
                    price_bias = float(np.mean(settle_price[hist0:start]-price_base[hist0:start]))
                    prf[start:] = np.maximum(0.001, price_base[start:]+price_bias)
                repl = adjustment_dispatch((lf[start:]-pf[start:])*DT_H, prf[start:], plan[start:],
                                             current_soc, params, 6000.0, down, up)
                qseg_all = repl.purchase
                solve_time += repl.solve_time_s
                adjust[start:stop] = qseg_all[:stop-start]
            used_load_f[start:stop] = lf[start:stop]
            used_pv_f[start:stop] = pf[start:stop]
            used_price_f[start:stop] = prf[start:stop]
            ex = causal_execute(adjust[start:stop], load_a_kw[start:stop]*DT_H, pv_a_kw[start:stop]*DT_H,
                                current_soc, params)
            for k in arrays: arrays[k][start:stop] = ex[k]
            current_soc = float(ex["soc_end"][-1])
        frame, metric = solution_frame(g, strategy, plan, adjust, arrays, settle_price, used_price_f,
                                       used_load_f, used_pv_f, "OPTIMAL_CAUSAL_MPC_4X", solve_time, params)
        rows.append(frame); metrics.append(metric); soc = current_soc
    return pd.concat(rows, ignore_index=True), pd.DataFrame(metrics)


def aggregate_baseline(metrics, problem, label):
    return {
        "problem": problem, "strategy": label, "days": int(len(metrics)),
        "total_cost_yuan": float(metrics.cost_yuan.sum()),
        "mean_daily_cost_yuan": float(metrics.cost_yuan.mean()),
        "total_final_purchase_kwh": float(metrics.final_purchase_kwh.sum()),
        "total_emergency_purchase_kwh": float(metrics.emergency_purchase_kwh.sum()),
        "total_storage_throughput_kwh": float(metrics.storage_throughput_kwh.sum()),
        "total_curtailment_kwh": float(metrics.curtailment_kwh.sum()),
        "max_balance_residual_kwh": float(metrics.max_energy_balance_residual_kwh.max()),
        "max_soc_residual_kwh": float(metrics.max_soc_residual_kwh.max()),
        "solve_time_s": float(metrics.solve_time_s.sum()),
    }


def q1_baselines(q1, params):
    price = pd.to_numeric(q1.iloc[:,1]).to_numpy(float)
    load = pd.to_numeric(q1.iloc[:,2]).to_numpy(float)*DT_H
    pv = pd.to_numeric(q1.iloc[:,3]).to_numpy(float)*DT_H
    net = load-pv
    results = []
    q = np.maximum(net,0); w=np.maximum(-net,0)
    results.append({"problem":"Q1","strategy":"no_storage","days":1,"total_cost_yuan":float(price@q),
                    "mean_daily_cost_yuan":float(price@q),"total_final_purchase_kwh":float(q.sum()),
                    "total_emergency_purchase_kwh":0.0,"total_storage_throughput_kwh":0.0,
                    "total_curtailment_kwh":float(w.sum()),"max_balance_residual_kwh":0.0,"max_soc_residual_kwh":0.0,"solve_time_s":0.0})
    lo,hi=np.quantile(price,[.25,.75])
    fixed=deterministic_dispatch(net,price,6000,params,terminal_soc_kwh=6000,
                                 charge_allowed=(price<=lo)|(net<0),discharge_allowed=(price>=hi))
    opt=deterministic_dispatch(net,price,6000,params,terminal_soc_kwh=6000)
    for name,sol in [("fixed_peak_valley_rule",fixed),("deterministic_lp",opt)]:
        results.append({"problem":"Q1","strategy":name,"days":1,"total_cost_yuan":float(price@sol.purchase),
                        "mean_daily_cost_yuan":float(price@sol.purchase),"total_final_purchase_kwh":float(sol.purchase.sum()),
                        "total_emergency_purchase_kwh":0.0,"total_storage_throughput_kwh":float((sol.charge+sol.discharge).sum()),
                        "total_curtailment_kwh":float(sol.curtailment.sum()),"max_balance_residual_kwh":sol.max_eq_residual,
                        "max_soc_residual_kwh":sol.max_eq_residual,"solve_time_s":sol.solve_time_s})
    return results


def oracle_full_year(ts, dynamic, params):
    g=ts[ts.date.isin(DATES)].sort_values(["date","interval_index"])
    price=g["price_actual"].to_numpy(float) if dynamic else g["price_static"].to_numpy(float)
    net=(g["load_actual_kw"].to_numpy(float)-g["pv_actual_kw"].to_numpy(float))*DT_H
    sol=deterministic_dispatch(net,price,6000,params,terminal_soc_kwh=6000)
    return {"problem":"Q4" if dynamic else "Q2","strategy":"oracle_perfect_information_lower_bound",
            "days":334,"total_cost_yuan":float(price@sol.purchase),"mean_daily_cost_yuan":float(price@sol.purchase/334),
            "total_final_purchase_kwh":float(sol.purchase.sum()),"total_emergency_purchase_kwh":0.0,
            "total_storage_throughput_kwh":float((sol.charge+sol.discharge).sum()),
            "total_curtailment_kwh":float(sol.curtailment.sum()),"max_balance_residual_kwh":sol.max_eq_residual,
            "max_soc_residual_kwh":sol.max_eq_residual,"solve_time_s":sol.solve_time_s}


def sensitivity_table(q1, fc, margins, scenarios, ts, params):
    rows=[]
    price=pd.to_numeric(q1.iloc[:,1]).to_numpy(float); net=(pd.to_numeric(q1.iloc[:,2]).to_numpy(float)-pd.to_numeric(q1.iloc[:,3]).to_numpy(float))*DT_H
    for label,p in [
        ("eta_each_0.85",StorageParams(eta_charge=.85,eta_discharge=.85)),
        ("eta_each_0.90",params),
        ("roundtrip_eta_0.90",StorageParams(eta_charge=np.sqrt(.9),eta_discharge=np.sqrt(.9))),
        ("capacity_80pct",StorageParams(9600,960,8640,params.max_energy_kwh,.9,.9)),
        ("capacity_120pct",StorageParams(14400,1440,12960,params.max_energy_kwh,.9,.9)),
        ("power_75pct",StorageParams(max_energy_kwh=625)),
        ("power_125pct",StorageParams(max_energy_kwh=1041.6666667)),
    ]:
        sol=deterministic_dispatch(net,price,6000,p,terminal_soc_kwh=6000)
        rows.append({"scope":"Q1","parameter":"physical","setting":label,"date":"typical_day","cost_yuan":float(price@sol.purchase),"planned_kwh":float(sol.purchase.sum()),"objective":sol.objective,"solve_time_s":sol.solve_time_s})
    residual=fc[fc.date.isin(DATES)].groupby("date")["net_load_residual_kw"].apply(lambda x: float(np.mean(np.abs(x))))
    date=residual.idxmax(); f=fc[fc.date==date].sort_values("interval_index"); m=margins[margins.target_date==date]; j=scenarios[scenarios.target_date==date]
    g=ts[ts.date==date].sort_values("interval_index"); price_f=g["price_static"].to_numpy(float)
    for n in [4,8,12]:
      for alpha,risk in [(.85,.2),(.90,0),(.90,.2),(.90,.5),(.95,.2)]:
        sol=plan_for_day("cvar",f,m,j,price_f,6000,params,n,alpha,risk,5.0,False)
        ex=causal_execute(sol.purchase,g.load_actual_kw.to_numpy(float)*DT_H,g.pv_actual_kw.to_numpy(float)*DT_H,6000,params)
        cost=float(price_f@sol.purchase + 5*price_f@ex["emergency"])
        rows.append({"scope":"Q2_extreme_day","parameter":"cvar","setting":f"S={n},alpha={alpha},lambda={risk}","date":str(date.date()),"cost_yuan":cost,"planned_kwh":float(sol.purchase.sum()),"objective":sol.objective,"solve_time_s":sol.solve_time_s})
    for mult in [3.0,5.0,8.0]:
        sol=plan_for_day("cvar",f,m,j,price_f,6000,params,8,.90,.20,mult,False)
        ex=causal_execute(sol.purchase,g.load_actual_kw.to_numpy(float)*DT_H,g.pv_actual_kw.to_numpy(float)*DT_H,6000,params)
        cost=float(price_f@sol.purchase + mult*price_f@ex["emergency"])
        rows.append({"scope":"Q2_extreme_day","parameter":"emergency_multiplier","setting":mult,"date":str(date.date()),"cost_yuan":cost,"planned_kwh":float(sol.purchase.sum()),"objective":sol.objective,"solve_time_s":sol.solve_time_s})
    for target in [5000.,6000.,7000.]:
        js,S=selected_scenarios(j,8); lr=js.load_residual_kw.to_numpy(float).reshape(S,144); pr=js.pv_residual_kw.to_numpy(float).reshape(S,144)
        load_s=np.maximum(0,f.load_pred_selected_kw.to_numpy(float)[None,:]+lr)*DT_H
        pv_s=np.maximum(0,f.pv_pred_selected_kw.to_numpy(float)[None,:]+pr)*DT_H
        sol=stochastic_cvar_plan(load_s,pv_s,np.tile(price_f,(S,1)),6000,params,5,.9,.2,target)
        rows.append({"scope":"Q2_extreme_day","parameter":"terminal_soc_kwh","setting":target,"date":str(date.date()),"cost_yuan":np.nan,"planned_kwh":float(sol.purchase.sum()),"objective":sol.objective,"solve_time_s":sol.solve_time_s})
    return pd.DataFrame(rows), date


def representative_summary(daily, fc):
    fixed={pd.Timestamp("2025-03-20"),pd.Timestamp("2025-06-21"),pd.Timestamp("2025-09-23"),pd.Timestamp("2025-12-21")}
    err=fc[fc.date.isin(DATES)].groupby("date")["net_load_residual_kw"].apply(lambda x: float(np.mean(np.abs(x))))
    extreme=err.idxmax(); fixed.add(extreme)
    rows=[]
    daily=daily.copy(); daily["date_dt"]=pd.to_datetime(daily.date)
    for d in sorted(fixed):
        for _,r in daily[daily.date_dt==d].iterrows():
            rows.append({"category":"specified_or_extreme","date":str(d.date()),"strategy_name":r.strategy_name,
                         "cost_yuan":r.cost_yuan,"emergency_purchase_kwh":r.emergency_purchase_kwh,
                         "soc_end_kwh":r.soc_end_kwh,"mean_abs_net_forecast_error_kw":err.loc[d]})
    for pct in [1,5,10]:
        cutoff=err.quantile(1-pct/100); ds=set(err[err>=cutoff].index)
        for s,g in daily[daily.date_dt.isin(ds)].groupby("strategy_name"):
            rows.append({"category":f"worst_{pct}pct_forecast_error","date":"aggregate","strategy_name":s,
                         "cost_yuan":float(g.cost_yuan.mean()),"emergency_purchase_kwh":float(g.emergency_purchase_kwh.mean()),
                         "soc_end_kwh":float(g.soc_end_kwh.mean()),"mean_abs_net_forecast_error_kw":float(err[err>=cutoff].mean())})
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--data-root",type=Path,required=True); ap.add_argument("--output-root",type=Path,required=True)
    ap.add_argument("--scenario-count",type=int,default=8)
    args=ap.parse_args(); root=args.data_root.resolve(); out=args.output_root.resolve(); out.mkdir(parents=True,exist_ok=True)
    started=perf_counter(); params=StorageParams(); ts,fc,margins,scenarios,official,q1=read_inputs(root)
    all_rows=[]; all_metrics=[]; baselines=q1_baselines(q1,params)
    base_q1,price_q1,load_q1,pv_q1,opt_q1,ex_q1=q1_outputs(q1,params)
    official_labels=ts[ts.date==pd.Timestamp("2025-01-01")].sort_values("interval_index")["output_interval_label"].to_numpy()
    base_q1["output_interval_label"]=official_labels
    q1frame,q1metric=solution_frame(base_q1,"result1",opt_q1.purchase,opt_q1.purchase,ex_q1,price_q1,price_q1,load_q1,pv_q1,"OPTIMAL_DETERMINISTIC_LP",opt_q1.solve_time_s,params)
    all_rows.append(q1frame); all_metrics.append(pd.DataFrame([q1metric]))
    # Q2 baselines and official CVaR result.
    metric_sets={}
    for mode in ["no_storage","fixed_rule","point"]:
        _,mm=simulate_q2(ts,fc,margins,scenarios,mode,"baseline",params,False,False,args.scenario_count)
        metric_sets[mode]=mm; baselines.append(aggregate_baseline(mm,"Q2",mode))
    q2,m2=simulate_q2(ts,fc,margins,scenarios,"safety","result2",params,False,True,args.scenario_count)
    all_rows.append(q2); all_metrics.append(m2); baselines.append(aggregate_baseline(m2,"Q2","safety_margin_lp"))
    _,mcvar=simulate_q2(ts,fc,margins,scenarios,"cvar","baseline",params,False,False,args.scenario_count)
    baselines.append(aggregate_baseline(mcvar,"Q2","cvar_two_stage"))
    # Q3 causal rolling MPC.
    q3,m3=simulate_mpc(ts,fc,official,"result3",params,False)
    all_rows.append(q3); all_metrics.append(m3); baselines.append(aggregate_baseline(m3,"Q3","rolling_mpc_4x"))
    # Q4 dynamic-price joint CVaR and rolling MPC.
    q42,m42=simulate_q2(ts,fc,margins,scenarios,"cvar","result4-2",params,True,True,args.scenario_count)
    all_rows.append(q42); all_metrics.append(m42); baselines.append(aggregate_baseline(m42,"Q4-2","joint_cvar"))
    q43,m43=simulate_mpc(ts,fc,official,"result4-3",params,True)
    all_rows.append(q43); all_metrics.append(m43); baselines.append(aggregate_baseline(m43,"Q4-3","dynamic_price_rolling_mpc"))
    baselines.append(oracle_full_year(ts,False,params)); baselines.append(oracle_full_year(ts,True,params))
    sol=pd.concat(all_rows,ignore_index=True)
    daily=pd.concat(all_metrics,ignore_index=True)
    # Exact cost and constraint checks before writing.
    if "PROVISIONAL" in " ".join(sol.solver_status.astype(str).unique()): raise AssertionError("provisional status remains")
    if sol.duplicated(["strategy_name","date","interval_index"]).any(): raise AssertionError("duplicate solution key")
    if daily.max_energy_balance_residual_kwh.max()>1e-5 or daily.max_soc_residual_kwh.max()>1e-5: raise AssertionError("hard-constraint residual")
    if daily.simultaneous_charge_discharge_intervals.sum()!=0: raise AssertionError("simultaneous charge/discharge")
    sol.to_csv(out/"solution_long.csv",index=False,encoding="utf-8-sig",float_format="%.8f")
    daily.to_csv(out/"daily_metrics.csv",index=False,encoding="utf-8-sig",float_format="%.8f")
    bdf=pd.DataFrame(baselines); no=float(bdf[(bdf.problem=="Q2")&(bdf.strategy=="no_storage")].total_cost_yuan.iloc[0])
    bdf["saving_vs_q2_no_storage_pct"]=np.where(bdf.problem=="Q2",(no-bdf.total_cost_yuan)/no,np.nan)
    bdf.to_csv(out/"baseline_results.csv",index=False,encoding="utf-8-sig",float_format="%.8f")
    sens,extreme=sensitivity_table(q1,fc,margins,scenarios,ts,params)
    sens.to_csv(out/"sensitivity_results.csv",index=False,encoding="utf-8-sig",float_format="%.8f")
    representative_summary(daily,fc).to_csv(out/"representative_day_summary.csv",index=False,encoding="utf-8-sig",float_format="%.8f")
    log={"seed":SEED,"scenario_count":args.scenario_count,"runtime_s":perf_counter()-started,
         "rows":len(sol),"strategies":sol.strategy_name.value_counts().to_dict(),"extreme_forecast_error_date":str(extreme.date()),
         "max_balance_residual_kwh":float(daily.max_energy_balance_residual_kwh.max()),
         "max_soc_residual_kwh":float(daily.max_soc_residual_kwh.max()),
         "simultaneous_charge_discharge_intervals":int(daily.simultaneous_charge_discharge_intervals.sum()),
         "solver_statuses":sorted(sol.solver_status.unique().tolist())}
    (out/"solver_log.json").write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(log,ensure_ascii=False))


if __name__=="__main__": main()
