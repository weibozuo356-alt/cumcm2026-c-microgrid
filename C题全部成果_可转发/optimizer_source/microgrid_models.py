"""Linear optimization models for CUMCM 2026 Problem C.

All interval energy variables are measured at the AC bus in kWh.  Charging
and discharging efficiencies appear only in the battery state equation.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Optional

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix


@dataclass(frozen=True)
class StorageParams:
    capacity_kwh: float = 12000.0
    soc_min_kwh: float = 1200.0
    soc_max_kwh: float = 10800.0
    max_energy_kwh: float = 5000.0 / 6.0
    eta_charge: float = 0.9
    eta_discharge: float = 0.9


@dataclass
class LPSolution:
    purchase: np.ndarray
    charge: np.ndarray
    discharge: np.ndarray
    soc_end: np.ndarray
    curtailment: np.ndarray
    emergency: np.ndarray
    objective: float
    status: str
    solve_time_s: float
    max_eq_residual: float


def _solve(c, A_eq, b_eq, bounds, A_ub=None, b_ub=None):
    started = perf_counter()
    result = linprog(
        c,
        A_ub=A_ub.tocsr() if A_ub is not None else None,
        b_ub=b_ub,
        A_eq=A_eq.tocsr(),
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
        options={"primal_feasibility_tolerance": 1e-8, "dual_feasibility_tolerance": 1e-8},
    )
    elapsed = perf_counter() - started
    if not result.success:
        raise RuntimeError(f"LP failed: status={result.status}; {result.message}")
    residual = float(np.max(np.abs(A_eq.tocsr() @ result.x - b_eq))) if len(b_eq) else 0.0
    return result, elapsed, residual


def deterministic_dispatch(
    net_load_kwh: np.ndarray,
    price: np.ndarray,
    soc0_kwh: float,
    params: StorageParams = StorageParams(),
    terminal_soc_kwh: Optional[float] = None,
    charge_allowed: Optional[np.ndarray] = None,
    discharge_allowed: Optional[np.ndarray] = None,
) -> LPSolution:
    """Minimize scheduled purchase cost for a deterministic trajectory."""
    net = np.asarray(net_load_kwh, dtype=float)
    price = np.asarray(price, dtype=float)
    T = len(net)
    if len(price) != T:
        raise ValueError("price and net load lengths differ")
    # Block order: q, c, p, E, w.
    q0, c0, p0, e0, w0 = 0, T, 2 * T, 3 * T, 4 * T
    n = 5 * T
    obj = np.zeros(n)
    obj[q0:q0 + T] = price
    obj[c0:c0 + T] = 1e-8
    obj[p0:p0 + T] = 1e-8
    rows = 2 * T + (1 if terminal_soc_kwh is not None else 0)
    A = lil_matrix((rows, n), dtype=float)
    b = np.zeros(rows)
    for t in range(T):
        # q + p - c - w = load - PV.
        A[t, q0 + t] = 1.0
        A[t, p0 + t] = 1.0
        A[t, c0 + t] = -1.0
        A[t, w0 + t] = -1.0
        b[t] = net[t]
        # E_t - E_{t-1} - eta_c*c_t + p_t/eta_d = 0.
        r = T + t
        A[r, e0 + t] = 1.0
        A[r, c0 + t] = -params.eta_charge
        A[r, p0 + t] = 1.0 / params.eta_discharge
        if t:
            A[r, e0 + t - 1] = -1.0
        else:
            b[r] = soc0_kwh
    if terminal_soc_kwh is not None:
        A[-1, e0 + T - 1] = 1.0
        b[-1] = terminal_soc_kwh
    ca = np.ones(T, dtype=bool) if charge_allowed is None else np.asarray(charge_allowed, dtype=bool)
    da = np.ones(T, dtype=bool) if discharge_allowed is None else np.asarray(discharge_allowed, dtype=bool)
    bounds = (
        [(0, None)] * T
        + [(0, params.max_energy_kwh if ca[t] else 0.0) for t in range(T)]
        + [(0, params.max_energy_kwh if da[t] else 0.0) for t in range(T)]
        + [(params.soc_min_kwh, params.soc_max_kwh)] * T
        + [(0, None)] * T
    )
    res, elapsed, residual = _solve(obj, A, b, bounds)
    x = res.x
    return LPSolution(
        purchase=x[q0:q0 + T], charge=x[c0:c0 + T], discharge=x[p0:p0 + T],
        soc_end=x[e0:e0 + T], curtailment=x[w0:w0 + T], emergency=np.zeros(T),
        objective=float(res.fun), status="OPTIMAL", solve_time_s=elapsed, max_eq_residual=residual,
    )


def adjustment_dispatch(
    net_load_kwh: np.ndarray,
    price_forecast: np.ndarray,
    original_plan_kwh: np.ndarray,
    soc0_kwh: float,
    params: StorageParams = StorageParams(),
    terminal_soc_kwh: float = 6000.0,
    down_multiplier: float = 0.5,
    up_multiplier: float = 1.5,
) -> LPSolution:
    """Replan a remaining horizon under the additive adjustment settlement."""
    net = np.asarray(net_load_kwh, dtype=float)
    price = np.asarray(price_forecast, dtype=float)
    plan = np.asarray(original_plan_kwh, dtype=float)
    T = len(net)
    # q, c, p, E, w, up, down.
    q0, c0, p0, e0, w0, u0, d0 = 0, T, 2*T, 3*T, 4*T, 5*T, 6*T
    n = 7*T
    obj = np.zeros(n)
    obj[c0:c0+T] = 1e-8
    obj[p0:p0+T] = 1e-8
    obj[u0:u0+T] = up_multiplier * price
    obj[d0:d0+T] = down_multiplier * price
    A = lil_matrix((3*T + 1, n), dtype=float)
    b = np.zeros(3*T + 1)
    for t in range(T):
        A[t, q0+t] = 1.0; A[t, p0+t] = 1.0; A[t, c0+t] = -1.0; A[t, w0+t] = -1.0
        b[t] = net[t]
        r = T+t
        A[r, e0+t] = 1.0; A[r, c0+t] = -params.eta_charge; A[r, p0+t] = 1.0/params.eta_discharge
        if t: A[r, e0+t-1] = -1.0
        else: b[r] = soc0_kwh
        # q - up + down = original plan.
        r = 2*T+t
        A[r, q0+t] = 1.0; A[r, u0+t] = -1.0; A[r, d0+t] = 1.0
        b[r] = plan[t]
    A[-1, e0+T-1] = 1.0
    b[-1] = terminal_soc_kwh
    bounds = (
        [(0, None)]*T + [(0, params.max_energy_kwh)]*T + [(0, params.max_energy_kwh)]*T
        + [(params.soc_min_kwh, params.soc_max_kwh)]*T + [(0, None)]*T
        + [(0, None)]*T + [(0, None)]*T
    )
    res, elapsed, residual = _solve(obj, A, b, bounds)
    x = res.x
    return LPSolution(
        purchase=x[q0:q0+T], charge=x[c0:c0+T], discharge=x[p0:p0+T],
        soc_end=x[e0:e0+T], curtailment=x[w0:w0+T], emergency=np.zeros(T),
        objective=float(res.fun), status="OPTIMAL", solve_time_s=elapsed, max_eq_residual=residual,
    )


def stochastic_cvar_plan(
    load_scenarios_kwh: np.ndarray,
    pv_scenarios_kwh: np.ndarray,
    price_scenarios: np.ndarray,
    soc0_kwh: float,
    params: StorageParams = StorageParams(),
    emergency_multiplier: float = 5.0,
    alpha: float = 0.90,
    risk_weight: float = 0.20,
    terminal_soc_kwh: Optional[float] = None,
) -> LPSolution:
    """Two-stage LP: common day-ahead purchase, scenario recourse, mean+CVaR cost."""
    load = np.asarray(load_scenarios_kwh, dtype=float)
    pv = np.asarray(pv_scenarios_kwh, dtype=float)
    prices = np.asarray(price_scenarios, dtype=float)
    if load.shape != pv.shape or prices.shape != load.shape:
        raise ValueError("scenario arrays must have identical S x T shapes")
    S, T = load.shape
    target = soc0_kwh if terminal_soc_kwh is None else terminal_soc_kwh
    # q; for each scenario [c,p,E,w,emergency]; z; u_s.
    q0 = 0
    block0 = T
    block = 5*T
    z_idx = block0 + S*block
    u0 = z_idx + 1
    n = u0 + S
    obj = np.zeros(n)
    obj[q0:q0+T] = prices.mean(axis=0)
    for s in range(S):
        base = block0 + s*block
        obj[base:base+T] = 1e-8 / S
        obj[base+T:base+2*T] = 1e-8 / S
        obj[base+4*T:base+5*T] = emergency_multiplier * prices[s] / S
    obj[z_idx] = risk_weight
    obj[u0:u0+S] = risk_weight / ((1-alpha)*S)
    eq_rows = S*(2*T+1)
    Aeq = lil_matrix((eq_rows, n), dtype=float)
    beq = np.zeros(eq_rows)
    for s in range(S):
        base = block0 + s*block
        c0, p0, e0, w0, m0 = base, base+T, base+2*T, base+3*T, base+4*T
        ro = s*(2*T+1)
        net = load[s] - pv[s]
        for t in range(T):
            r = ro+t
            Aeq[r, q0+t] = 1.0; Aeq[r, m0+t] = 1.0; Aeq[r, p0+t] = 1.0
            Aeq[r, c0+t] = -1.0; Aeq[r, w0+t] = -1.0
            beq[r] = net[t]
            r = ro+T+t
            Aeq[r, e0+t] = 1.0; Aeq[r, c0+t] = -params.eta_charge; Aeq[r, p0+t] = 1.0/params.eta_discharge
            if t: Aeq[r, e0+t-1] = -1.0
            else: beq[r] = soc0_kwh
        Aeq[ro+2*T, e0+T-1] = 1.0
        beq[ro+2*T] = target
    Aub = lil_matrix((S, n), dtype=float)
    bub = np.zeros(S)
    for s in range(S):
        base = block0+s*block
        m0 = base+4*T
        Aub[s, q0:q0+T] = prices[s]
        Aub[s, m0:m0+T] = emergency_multiplier*prices[s]
        Aub[s, z_idx] = -1.0
        Aub[s, u0+s] = -1.0
    bounds = [(0, None)]*T
    for _ in range(S):
        bounds += [(0, params.max_energy_kwh)]*T
        bounds += [(0, params.max_energy_kwh)]*T
        bounds += [(params.soc_min_kwh, params.soc_max_kwh)]*T
        bounds += [(0, None)]*T
        bounds += [(0, None)]*T
    bounds += [(0, None)] + [(0, None)]*S
    res, elapsed, residual = _solve(obj, Aeq, beq, bounds, Aub, bub)
    q = res.x[q0:q0+T]
    # Return the first scenario's recourse only for diagnostics; actual execution is causal.
    base = block0
    return LPSolution(
        purchase=q, charge=res.x[base:base+T], discharge=res.x[base+T:base+2*T],
        soc_end=res.x[base+2*T:base+3*T], curtailment=res.x[base+3*T:base+4*T],
        emergency=res.x[base+4*T:base+5*T], objective=float(res.fun), status="OPTIMAL",
        solve_time_s=elapsed, max_eq_residual=residual,
    )


def causal_execute(
    purchase_kwh: np.ndarray,
    load_actual_kwh: np.ndarray,
    pv_actual_kwh: np.ndarray,
    soc0_kwh: float,
    params: StorageParams = StorageParams(),
):
    """Greedy causal balancing after each interval's actual load and PV are observed."""
    q = np.asarray(purchase_kwh, dtype=float)
    load = np.asarray(load_actual_kwh, dtype=float)
    pv = np.asarray(pv_actual_kwh, dtype=float)
    T = len(q)
    charge = np.zeros(T); discharge = np.zeros(T); emergency = np.zeros(T)
    curtail = np.zeros(T); start = np.zeros(T); end = np.zeros(T)
    soc = float(soc0_kwh)
    for t in range(T):
        start[t] = soc
        surplus = q[t] + pv[t] - load[t]
        if surplus >= 0:
            charge[t] = min(surplus, params.max_energy_kwh, (params.soc_max_kwh-soc)/params.eta_charge)
            curtail[t] = max(0.0, surplus-charge[t])
        else:
            deficit = -surplus
            discharge[t] = min(deficit, params.max_energy_kwh, (soc-params.soc_min_kwh)*params.eta_discharge)
            emergency[t] = max(0.0, deficit-discharge[t])
        soc = soc + params.eta_charge*charge[t] - discharge[t]/params.eta_discharge
        if abs(soc-params.soc_min_kwh) < 1e-8: soc = params.soc_min_kwh
        if abs(soc-params.soc_max_kwh) < 1e-8: soc = params.soc_max_kwh
        end[t] = soc
    return {"charge": charge, "discharge": discharge, "emergency": emergency,
            "curtailment": curtail, "soc_start": start, "soc_end": end}

