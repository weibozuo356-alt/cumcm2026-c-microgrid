# 官方 Excel 导出与验证

本目录提供五个官方结果工作簿的独立导出和验证入口。最终策略数据为上一级目录的 `solution_long.csv`；输出目录为上一级的 `official_results/`。

复核现有工作簿：

```powershell
python .\template_exporter\validate_official_results.py `
  --workbook-root .\official_results `
  --data-root . `
  --solution .\solution_long.csv
```

从 `source_inputs/附件5/` 的官方模板重新生成：

```powershell
\.\template_exporter\run_export.ps1
```

新导出的公式需要由桌面版 Microsoft Excel 计算并写入缓存。逐个打开五个文件，执行“公式 → 全部重算”、保存并关闭后，再运行严格验证：

```powershell
python .\template_exporter\validate_official_results.py `
  --workbook-root .\official_results `
  --data-root . `
  --solution .\solution_long.csv
```

依赖：Python 3.10+、pandas、numpy、openpyxl。若跳过 Excel 重算，严格验证会把公式缓存缺失列为问题，这是预期保护机制。
