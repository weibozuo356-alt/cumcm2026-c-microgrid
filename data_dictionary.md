# 数据字典

## processed_timeseries.csv

| 列 | 类型 | 单位 | 来源 | 最早可获得时刻/说明 |
|---|---|---|---|---|
| date | date | 日 | 附件2 | 逻辑运行日 |
| interval_index | int | 1—144 | 附件列序 | 内部唯一时间索引 |
| source_time_label | string | 时刻 | 附件2表头 | 原始标签；第144项为次日0:00 |
| output_interval_label | string | 区间 | 官方模板 | 第t项与interval_index=t严格对应 |
| interval_end_timestamp | datetime | 时刻 | 计算 | date + 10×interval_index分钟 |
| load_actual_kw | float | kW | 附件2/小区负载 | 区间结束后可获得；不得用于该区间事前决策 |
| pv_actual_kw | float | kW | 附件2/光伏实际 | 区间结束后可获得；不得用于该区间事前决策 |
| price_actual | float | 元/kWh | 附件4 | 动态电价；可获得时刻由Q4建模假设决定 |
| price_static | float | 元/kWh | 附件1 | Q1—Q3每日相同电价曲线 |
| forecast_issue_time | datetime | 时刻 | 附件3 | 当日0:00版本，用于全天基准计划 |
| forecast_lead_h | int | 小时 | 附件3列名 | ceil(interval_index/6) |
| pv_forecast_kw | float | kW | 附件3 | 对应0:00发布版本，分段常数展开到10分钟 |

## forecast_results.csv

包含实际值、前一日同刻、上周同日同刻、历史扩展同刻均值、工作日/周末扩展均值、扩展窗口岭回归、官方光伏预测和官方预测偏差校正。`*_selected_*`每天只根据前一日结束前的累计MAE选择候选模型，`*_selected_model`记录选择结果；它们是场景残差默认基准。所有预测和模型选择只使用目标时刻之前已获得的信息。

## solution_long.csv 接口

| 列 | 单位/含义 |
|---|---|
| date | 逻辑运行日 |
| interval_index | 1—144 |
| output_interval_label | 官方模板显示区间，必须与索引匹配 |
| purchase_plan_kwh | 0:00确定的计划购电量，kWh |
| purchase_adjust_kwh | 采用的接口解释：更新预测后调整得到的绝对计划购电量，非差值，kWh；无调整问题等于purchase_plan_kwh |
| purchase_final_kwh | 最终实际外部购电量，kWh；Q3口径为purchase_adjust_kwh + purchase_emergency_kwh |
| purchase_emergency_kwh | 紧急购电量，kWh |
| charge_kwh / discharge_kwh | 交流侧充/放电电量，kWh |
| soc_start_kwh / soc_end_kwh | 区间起/末储电量，kWh |
| curtailment_kwh | 弃光电量，kWh |
| cost_plan / cost_adjust / cost_emergency / cost_total | 区间费用，元 |
| strategy_name | `result1`、`result2`、`result3`、`result4-2`、`result4-3`之一 |
| solver_status | 求解器状态；最终官方文件不得是PROVISIONAL状态 |

## 储能统一口径

- 容量 12000 kWh；允许储电量 1200—10800 kWh；初值 6000 kWh。
- 最大充/放电功率 5000 kW，对应每十分钟 833.3333 kWh。
- 主模型充、放电效率均为0.9；建议状态式 `soc_end = soc_start + 0.9*charge_kwh - discharge_kwh/0.9`。
- Q2—Q4跨日连续，不得每日重置。
