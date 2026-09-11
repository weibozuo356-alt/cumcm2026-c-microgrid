# 目标函数与约束

## 1. 统一物理约束

对每个日、区间和适用场景：

```text
q + e + G*Delta_t + p = L*Delta_t + c + w
E_t = E_(t-1) + eta_c*c - p/eta_d
1200 <= E_t <= 10800
0 <= c,p <= 833.333333
q,e,w >= 0
```

第一式在交流母线侧平衡电量；第二式只在 SOC 更新处计算效率，因此不会重复扣除损耗。没有售电变量。正电价、效率损耗和 `1e-8(c+p)` 的退化消除项共同排除同区间同时充放电；最终验证结果为 0 个同时充放电区间，故不需要二元变量或 MILP。

## 2. Q1 确定性 LP

```text
min sum_t pi_t*q_t
s.t. 统一物理约束，E_0=E_144=6000
```

固定规则基线仅允许在低价四分位区间或光伏富余区间充电，并仅允许在高价四分位区间放电；其余约束不变。

## 3. Q2 安全裕度与两阶段 CVaR

主结果的计划净负荷为：

```text
N_safe(d,t) = N_forecast(d,t) + max(0, Q_0.90[net-load residual | information before d])
```

计划 LP 仍采用 Q1 的结构，日初、日末规划 SOC 相同。实际执行时，计划购电不变，当前区间的真实缺口先由可用放电补足，剩余量进入 `e`；富余先充电，剩余进入 `w`。

两阶段随机 LP 中，第一阶段 `q_t` 对所有场景共同，第二阶段变量带场景索引。场景成本为：

```text
C_s = sum_t (pi_s,t*q_t + 5*pi_s,t*e_s,t)
CVaR_alpha = zeta + [1/((1-alpha)S)] sum_s xi_s
xi_s >= C_s-zeta, xi_s >= 0
min E[C_s] + lambda*CVaR_alpha
```

每个场景都有独立的能量平衡、SOC 动态、边界和终端约束。

## 4. Q3 调整模型

调整绝对量满足：

```text
qf_t = q0_t + u_t - v_t
u_t,v_t >= 0
```

主结算：

```text
C_main = sum_t [pi_t*q0_t + 1.5*pi_t*u_t + 0.5*pi_t*v_t + 5*pi_t*e_t]
```

替代净结算：

```text
C_alt = sum_t [pi_t*q0_t + 1.5*pi_t*u_t - 0.5*pi_t*v_t + 5*pi_t*e_t]
      = sum_t [pi_t*qf_t + 0.5*pi_t*u_t + 0.5*pi_t*v_t + 5*pi_t*e_t]
```

主结果使用第一种公式。每个更新时间优化剩余时域，只执行下一段；实际负荷与光伏揭示后的缺口由因果电池控制与紧急购电平衡。

## 5. Q4 动态价格

优化目标中的 `pi_forecast` 仅由前一日同刻价格及当前已观测残差构成。真实 `pi_actual` 不进入未来决策，只用于上式的事后费用复算。联合场景令 `(load residual, PV residual, price residual)` 从同一历史日轨迹共同抽取，而不是独立抽样。

