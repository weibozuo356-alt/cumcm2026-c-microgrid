# 2026全国大学生数学建模竞赛C题：微网调控

当前仓库保存C题数据工程、因果预测、不确定性场景生成、`solution_long.csv`接口、五个官方Excel导出器及验证结果。

## 当前进度

- 已完成附件1—4的数据审计和365×144统一长表。
- 已完成前一日同刻、上周同刻、扩展均值、工作日/周末、扩展岭回归、官方光伏预测及因果偏差校正。
- 已输出总体、月度、提前期和白天光伏的MAE、RMSE、WMAPE。
- 已生成负荷、光伏、净负荷、动态电价残差和961,920条无未来泄漏的联合日轨迹场景。
- 已实现五个官方模板的完整导出、公式重算和保存后重开验证。
- 当前五个结果文件使用因果零储能临时基线，仅用于验证导出链路；最终数值等待优化负责人提交`solution_long.csv`。

## 主要入口

- `A_handoff.md`：完整交接说明。
- `data_dictionary.md`：数据与优化接口定义。
- `data_audit.md`：数据和时间语义审计。
- `processed_timeseries.csv`：统一十分钟长表。
- `forecast_results.csv`、`forecast_metrics.csv`：预测结果与评价。
- `scenario_data/`：残差、轨迹场景和安全裕度。
- `template_exporter/`：Excel导出、验证及一键复现程序。
- `excel_validation_report.md`：五个结果文件验证状态。

## 一键复现

没有最终优化结果时：

```powershell
powershell -ExecutionPolicy Bypass -File .\template_exporter\run_all.ps1
```

收到最终优化结果后：

```powershell
powershell -ExecutionPolicy Bypass -File .\template_exporter\run_all.ps1 -Solution .\solution_long.csv
```

储能与时间映射等共同口径以`A_handoff.md`和`data_dictionary.md`为准。
