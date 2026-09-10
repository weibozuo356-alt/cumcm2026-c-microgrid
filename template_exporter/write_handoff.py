from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--solution", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    solution = pd.read_csv(args.solution, encoding="utf-8-sig", usecols=["strategy_name", "solver_status"])
    provisional = solution["solver_status"].astype(str).str.contains("PROVISIONAL", case=False).any()
    status = "五个Excel已完成结构与导出链路验证，但采用临时因果零储能基线；等待优化负责人提供最终solution_long.csv。" if provisional else "五个Excel已由最终solution_long.csv生成并完成重开验证。"
    text = rf"""# A 组交接说明

## 当前结论

{status}

## 已完成工作

1. 完整审计附件1—4的工作表、尺寸、日期、144区间完整性、缺失、重复、负值和数值范围。
2. 将附件2实际负荷/光伏、附件4动态电价、附件1静态电价和附件3的0:00版本预测统一为十分钟长表。
3. 实现严格按时间推进的前一日同刻、上周同日同刻、扩展窗口同刻均值、工作日/周末均值、扩展岭回归、官方光伏预测和因果偏差校正。
4. 输出总体、月度、提前期和白天光伏MAE/RMSE/WMAPE；夜间光伏未使用普通MAPE。
5. 构造负荷、光伏、净负荷、动态电价残差，完整日轨迹、联合轨迹场景和因果分位数安全裕度。
6. 建立solution_long接口、五个官方模板导出器、公式重算和保存后重开验证。

## 文件作用

| 文件/目录 | 作用 |
|---|---|
| `data_dictionary.md` | 列、单位、来源、可获得时刻与solution_long接口 |
| `data_audit.md` | 附件审计、题面/模板事实、解释和风险 |
| `processed_timeseries.csv` | 2025全年365×144统一长表 |
| `forecast_results.csv` | 全模型逐区间预测、实际与残差 |
| `forecast_metrics.csv` | MAE/RMSE/WMAPE及分组指标 |
| `scenario_data/` | 发布预测长表、残差、日轨迹、联合场景、分位数裕度及临时solution |
| `scenario_description.md` | 场景抽样方法和随机种子 |
| `template_exporter/` | 数据、导出、验证与一键复现程序 |
| `result1.xlsx`等五个文件 | 官方模板副本上的结果 |
| `excel_validation_report.md` | 保存后重开、合计、费用、紧急区间与SOC连续性验证 |

## 单位和储能口径

- 功率：kW；每10分钟电量：kWh，换算为功率乘`1/6`。
- 电价：元/kWh；费用：元。
- SOC：kWh；范围1200—10800，容量12000，初始6000。
- 最大充/放电功率5000 kW，对应每区间833.3333 kWh。
- 主状态式建议为`soc_end = soc_start + 0.9*charge - discharge/0.9`。
- Q2—Q4必须检查相邻日`前日soc_end == 次日soc_start`。

## 时间映射

- 内部`interval_index=1,...,144`。
- 附件宽表第t个值、处理长表第t行和模板第t个结果位置严格绑定。
- 模板首项`0:10-0:20`，末项`0:00-0:10+1`；禁止整体平移。
- 四小时汇总使用索引1—24、25—48、…、121—144，对应模板六个固定段。
- 附件3的24个整点提前期按每小时覆盖6个十分钟子区间展开；原始发布、目标时间和跨年映射保存在`official_forecasts_long.csv.gz`。

## 预测可获得时刻

- 日前负荷模型仅使用目标日前的实际历史和已知日历特征，在目标日0:00可得。
- 日前官方光伏使用目标日0:00发布版本；偏差校正仅使用过去日期残差。
- 滚动光伏使用当日0:00/6:00/12:00/18:00已经发布且覆盖目标区间的最新版本。
- 实际负荷、实际光伏只用于事后评价、紧急购电触发与残差，不进入相应事前计划。

## 不确定性与随机种子

- 固定随机种子：`20260910`。
- 每个目标日20条联合场景；只从严格早于目标日的同季节、同工作日类型完整日残差中抽样，保留144点日内相关性；样本不足时退化为全部既往日。

## 已知风险与歧义

| 类别 | 内容 |
|---|---|
| 题面事实 | Q3比较计划购电量和调整购电量，并对差额按0.5/1.5倍计价。 |
| 官方模板事实 | 调整购电量工作表与计划表同为144列绝对量格式。 |
| 采用的解释 | `purchase_adjust_kwh`为调整后的绝对计划量，不是增量；`purchase_final_kwh=调整量+紧急量`。 |
| 敏感性处理 | 如果团队统一接口确认其为增量，只需在导出前显式转换，不能静默复用当前字段。 |
| 时间歧义 | 附件时间标签与模板首区间表面相差10分钟；依据用户明确指令按序号一一对应。 |
| 预测歧义 | 附件3称“未来24小时整点预测”，主线采用小时内分段常数；可用线性插值做敏感性复算。 |
| 当前结果 | 若`solver_status`含PROVISIONAL，五个Excel仅是格式/链路可运行基线，不是最终最优策略。 |
| 团队仓库 | 用户给定GitHub仓库在2026-09-10核对时为空；采用了用户消息中的Q1→Q2→Q3→Q4总方案。 |

## 优化负责人读取方式

```python
import pandas as pd
ts = pd.read_csv("processed_timeseries.csv", parse_dates=["date", "interval_end_timestamp", "forecast_issue_time"])
forecast = pd.read_csv("forecast_results.csv", parse_dates=["date"])
scenarios = pd.read_csv("scenario_data/joint_scenarios.csv.gz")
margins = pd.read_csv("scenario_data/residual_quantile_margins.csv.gz")
```

请按`data_dictionary.md`生成最终`solution_long.csv`。`strategy_name`必须分别覆盖`result1`、`result2`、`result3`、`result4-2`、`result4-3`；最终`solver_status`不得含`PROVISIONAL`。

## 总负责人一键复现五个Excel

```powershell
powershell -ExecutionPolicy Bypass -File .\template_exporter\run_all.ps1 -Solution .\solution_long.csv
```

如果尚无最终解，省略`-Solution`会自动使用`scenario_data/provisional_solution_long.csv`跑通全链路。程序从官方模板副本开始，不改工作表名称、顺序和宽表表头；随后调用本机Excel重算公式并保存，再重新打开验证。
"""
    (root / "A_handoff.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
