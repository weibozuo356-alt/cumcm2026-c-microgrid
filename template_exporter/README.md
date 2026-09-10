# C题数据、预测、场景与Excel导出器

一键运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\template_exporter\run_all.ps1
```

若优化负责人已给出最终长表：

```powershell
powershell -ExecutionPolicy Bypass -File .\template_exporter\run_all.ps1 -Solution .\solution_long.csv
```

程序顺序执行数据审计、因果预测、场景生成、五个模板导出、Excel公式重算、保存后重开验证和交接文档更新。未提供最终解时，会使用`scenario_data/provisional_solution_long.csv`验证整条导出链路；该临时解采用零储能动作，不是最终优化结果。

依赖：Python 3.10+、pandas、numpy、openpyxl；Windows上安装Microsoft Excel可刷新工作簿公式缓存。

脚本：

- `data_pipeline.py`：审计、统一长表、预测、指标、场景与临时接口数据。
- `export_results.py`：从官方模板副本填充五个结果文件。
- `validate_results.py`：重开并检查合计、费用、SOC、紧急区间和公式错误。
- `write_handoff.py`：生成`A_handoff.md`。
