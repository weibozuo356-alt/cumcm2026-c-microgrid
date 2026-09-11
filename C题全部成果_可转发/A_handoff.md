# A 组数据、预测、场景与 Excel 交接说明

## 当前结论

数据审计、统一长表、严格因果预测、残差场景、五种最终策略长表和五个官方 Excel 均已生成。程序化验证全部通过，最终结果中不存在 `PROVISIONAL` 状态。提交前仅剩在桌面版 Microsoft Excel 中逐个执行“全部重算”、保存并目视复核。

## 已完成工作

1. 审计附件1—4的工作表、尺寸、日期、每日144区间、缺失、重复、异常值和时间映射。
2. 统一实际负荷、实际光伏、静态/动态电价和多发布时间光伏预测，生成365天×144区间长表。
3. 实现前一日同刻、上周同日同刻、历史扩展同刻均值、工作日/周末分组、扩展线性模型、官方光伏预测及因果偏差校正；训练与模型选择均按时间推进。
4. 计算 MAE、RMSE、WMAPE、白天光伏误差、分提前期和分月份误差；夜间光伏未使用普通 MAPE。
5. 生成负荷、光伏、净负荷和动态电价残差，完整日残差轨迹、联合场景和残差分位数安全裕度。
6. 接收并核验五种最终策略的 `solution_long.csv`，导出五个官方工作簿，并进行结构、费用、能量、SOC、紧急区间和时间错位检查。

## 文件作用

| 文件/目录 | 作用 |
|---|---|
| `data_dictionary.md` | 数据列、单位、来源、可获得时刻与接口定义 |
| `data_audit.md` | 附件审计、题面/模板事实、解释和敏感性处理 |
| `processed_timeseries.csv` | 2025全年365×144统一长表 |
| `forecast_results.csv` | 各候选模型逐区间预测、实际与残差 |
| `forecast_metrics.csv` | 总体、月度、提前期和白天误差指标 |
| `scenario_data/` | 发布预测、残差、完整日轨迹、联合场景和分位数裕度 |
| `scenario_description.md` | 场景生成方法与随机种子 |
| `optimizer_source/` | 确定性 LP、调整 LP、CVaR-LP 和因果执行器 |
| `simulation_source/` | 全年仿真、敏感性、官方结果导出与验证 |
| `template_exporter/` | 官方 Excel 导出与复核的独立入口 |
| `solution_long.csv` | 五个官方方案的统一区间级结果 |
| `daily_metrics.csv` | 逐日费用、能量、SOC、残差和求解状态 |
| `baseline_results.csv` | 基线、主方案、对照方案和 Oracle 汇总 |
| `official_results/` | 五个最终官方工作簿及逐文件验证报告 |
| `final_consistency_audit.md` | 三张核心 CSV 与五个 Excel 的交叉一致性审计 |
| `paper_data_handoff.md` | 正文数字、统一口径和图表取数指引 |
| `source_inputs/` | 题面、附件1—4、官方模板及论文格式文件 |

## 单位与储能口径

- 功率：kW；10分钟区间电量：kWh，换算为功率乘 `1/6`。
- 电价：元/kWh；费用：元。
- SOC：kWh；储能容量12,000 kWh，允许范围1,200—10,800 kWh，初始6,000 kWh。
- 最大充/放电功率5,000 kW，对应每区间最大充/放电量833.3333 kWh。
- 充电量与放电量均在交流侧，状态方程为 `soc_end=soc_start+0.9*charge-discharge/0.9`。
- Q2—Q4 相邻日满足“前日 `soc_end` = 次日 `soc_start`”，不做每日重置。

## 时间映射

- 内部统一 `interval_index=1,...,144`。
- 第 `t` 个计算结果写入模板第 `t` 个位置，不进行整体平移。
- 模板首区间为 `0:10-0:20`，末区间为 `0:00-0:10+1`。
- 四小时汇总使用索引1—24、25—48、…、121—144，对应六个固定时段。
- 附件3的每个整点预测覆盖随后六个10分钟区间；发布时间、目标时刻、提前期和跨日映射保存在 `scenario_data/official_forecasts_long.csv.gz`。

## 预测可获得时刻

- 日前预测只使用目标日前已经观测的历史实际值及已知日历信息。
- 日前光伏使用目标日0:00时已经发布的官方预测；偏差校正只使用此前日期残差。
- Q3/Q4-3 在0:00、6:00、12:00、18:00仅使用当时已发布且覆盖未来区间的最新预测。
- 实际负荷、实际光伏和实际动态电价只用于事后结算、评价与残差计算，不进入相应决策时刻的事前计划。

## 不确定性与随机种子

- 固定随机种子：`20260910`。
- 每个目标日构造联合净负荷—电价场景；只从严格早于目标日的同季节、同工作日类型完整日轨迹中抽样，保留144点日内相关性。
- Q2主方案采用历史残差90%分位数安全裕度；Q2 CVaR仅为增强对照。

## 已知风险与歧义

| 类别 | 事实与处理 |
|---|---|
| 题面事实 | Q3存在计划量、调整量及0.5/1.5倍差额结算，紧急购电按5倍计价。 |
| 模板事实 | 调整购电量表与计划表均为144列绝对量格式。 |
| 主文解释 | 采用“计划费 + 0.5倍下调违约费 + 1.5倍上调费 + 5倍紧急费”。 |
| 敏感性处理 | 替代净结算仅放入附录/敏感性，不与主文费用混用。 |
| 时间歧义 | 附件标签与模板首区间表面相差10分钟；按官方模板位置序号一一对应。 |
| 预测歧义 | 附件3整点预测按小时内分段常数展开；其他插值方式可作为敏感性分析。 |
| Oracle | 只表示完美信息下界，不是可执行策略，也未进入五个官方结果文件。 |
| Excel显示 | 程序化复核已通过；桌面版 Excel 的“全部重算并保存”仍需人工完成。 |

## 优化负责人读取方式

```python
import pandas as pd

ts = pd.read_csv("processed_timeseries.csv", parse_dates=["date"])
forecast = pd.read_csv("forecast_results.csv", parse_dates=["date"])
scenarios = pd.read_csv("scenario_data/joint_scenarios.csv.gz")
margins = pd.read_csv("scenario_data/residual_quantile_margins.csv.gz")
solution = pd.read_csv("solution_long.csv", parse_dates=["date"])
```

优化接口字段含义以 `data_dictionary.md` 为准，不得私自改变 `purchase_adjust_kwh`、SOC、充放电或费用字段的定义。

## 总负责人复现五个 Excel

仅复核现有最终工作簿：

```powershell
python .\template_exporter\validate_official_results.py `
  --workbook-root .\official_results `
  --data-root . `
  --solution .\solution_long.csv
```

从官方模板重新导出并复核：

```powershell
\.\template_exporter\run_export.ps1
```

随后在桌面版 Microsoft Excel 中逐个“全部重算”、保存并关闭，再运行：

```powershell
python .\template_exporter\validate_official_results.py `
  --workbook-root .\official_results `
  --data-root . `
  --solution .\solution_long.csv
```

完整重新求解需要源附件目录，并运行根目录 `run_all.ps1`。重新求解后必须再次导出、验证，再在桌面版 Excel 中全部重算和保存。
