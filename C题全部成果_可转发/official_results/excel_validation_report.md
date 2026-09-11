# Excel 验证报告

结论：**全部校验通过**。

输入：`solution_long.csv`

## 校验范围

- 工作表名称与顺序保持官方模板不变。
- 2025-02-01至2025-12-31共334天，每天144个区间。
- 第t个值按官方模板第t列写入；未整体平移时间。
- 充放电量展开为每天6个四小时段；省略号样例已删除。
- 连续正紧急购电区间已合并，同日多段分行，合并前后总量守恒。
- 全天购电量由Excel公式求和；费用与solution_long区间费用独立对比。
- 文件保存后重新打开，并扫描公式错误字符串。

## 文件结果

| 文件 | 状态 | 关键统计 |
|---|---|---|
| result1.xlsx | 通过 | `{"file": "result1.xlsx", "sheets": ["计划购电量", "充放电量"], "formula_errors": 0, "ellipsis_cells": 0, "independent_cost_max_diff": 7.6850028563058e-09, "intervals": 144, "purchase_total_kwh": 59482.69899839, "cost_total_yuan": 35126.948589249994}` |
| result2.xlsx | 通过 | `{"file": "result2.xlsx", "sheets": ["计划购电量", "充放电量", "紧急购电量"], "formula_errors": 0, "ellipsis_cells": 0, "independent_cost_max_diff": 3.920013114111498e-08, "plan_shape": [335, 147], "charge_date_rows": 334, "emergency_blank_rows": 0, "emergency_partial_rows": 0, "max_plan_diff": 5.820766091346741e-11, "max_plan_cost_diff": 7.275957614183426e-12, "charge_rows": 2005, "soc_crossday_max_diff": 0.0, "emergency_event_rows": 116, "emergency_total_kwh": 74579.33773900999}` |
| result3.xlsx | 通过 | `{"file": "result3.xlsx", "sheets": ["计划购电量", "调整购电量", "充放电量", "紧急购电量"], "formula_errors": 0, "ellipsis_cells": 0, "independent_cost_max_diff": 3.887987531925319e-08, "plan_shape": [335, 147], "max_adjust_diff": 8.731149137020111e-11, "max_adjust_cost_diff": 7.275957614183426e-12, "charge_date_rows": 334, "emergency_blank_rows": 0, "emergency_partial_rows": 0, "max_plan_diff": 7.275957614183426e-11, "max_plan_cost_diff": 7.275957614183426e-12, "charge_rows": 2005, "soc_crossday_max_diff": 0.0, "emergency_event_rows": 577, "emergency_total_kwh": 157058.99230570995}` |
| result4-2.xlsx | 通过 | `{"file": "result4-2.xlsx", "sheets": ["计划购电量", "充放电量", "紧急购电量"], "formula_errors": 0, "ellipsis_cells": 0, "independent_cost_max_diff": 4.576031642500311e-08, "plan_shape": [335, 147], "charge_date_rows": 334, "emergency_blank_rows": 0, "emergency_partial_rows": 0, "max_plan_diff": 5.820766091346741e-11, "max_plan_cost_diff": 1.4551915228366852e-11, "charge_rows": 2005, "soc_crossday_max_diff": 0.0, "emergency_event_rows": 341, "emergency_total_kwh": 223211.96810896002}` |
| result4-3.xlsx | 通过 | `{"file": "result4-3.xlsx", "sheets": ["计划购电量", "调整购电量", "充放电量", "紧急购电量"], "formula_errors": 0, "ellipsis_cells": 0, "independent_cost_max_diff": 4.3474983613123186e-08, "plan_shape": [335, 147], "max_adjust_diff": 7.275957614183426e-11, "max_adjust_cost_diff": 7.275957614183426e-12, "charge_date_rows": 334, "emergency_blank_rows": 0, "emergency_partial_rows": 0, "max_plan_diff": 7.275957614183426e-11, "max_plan_cost_diff": 7.275957614183426e-12, "charge_rows": 2005, "soc_crossday_max_diff": 0.0, "emergency_event_rows": 573, "emergency_total_kwh": 166074.70211448}` |
