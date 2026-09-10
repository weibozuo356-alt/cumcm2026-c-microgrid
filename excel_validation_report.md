# Excel 验证报告

结论：**结构与数值校验通过，但仍为临时基线，待优化结果替换**。

输入：`provisional_solution_long.csv`

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
| result1.xlsx | 通过 | `{"file": "result1.xlsx", "sheets": ["计划购电量", "充放电量"], "formula_errors": 0, "independent_cost_max_diff": 8.501999992915898e-07, "intervals": 144, "purchase_total_kwh": 61789.935402, "cost_total_yuan": 48052.046591000006}` |
| result2.xlsx | 通过 | `{"file": "result2.xlsx", "sheets": ["计划购电量", "充放电量", "紧急购电量"], "formula_errors": 0, "independent_cost_max_diff": 3.8944000380070065e-06, "plan_shape": [335, 147], "max_plan_diff": 7.275957614183426e-11, "max_plan_cost_diff": 1.4551915228366852e-11, "charge_rows": 2005, "soc_crossday_max_diff": 0.0, "emergency_event_rows": 5138, "emergency_total_kwh": 853232.2020210004}` |
| result3.xlsx | 通过 | `{"file": "result3.xlsx", "sheets": ["计划购电量", "调整购电量", "充放电量", "紧急购电量"], "formula_errors": 0, "independent_cost_max_diff": 3.815999889411614e-06, "plan_shape": [335, 147], "max_adjust_diff": 7.275957614183426e-11, "max_adjust_cost_diff": 1.4551915228366852e-11, "max_plan_diff": 7.275957614183426e-11, "max_plan_cost_diff": 7.275957614183426e-12, "charge_rows": 2005, "soc_crossday_max_diff": 0.0, "emergency_event_rows": 5172, "emergency_total_kwh": 1177318.5690499991}` |
| result4-2.xlsx | 通过 | `{"file": "result4-2.xlsx", "sheets": ["计划购电量", "充放电量", "紧急购电量"], "formula_errors": 0, "independent_cost_max_diff": 5.087999852548819e-06, "plan_shape": [335, 147], "max_plan_diff": 7.275957614183426e-11, "max_plan_cost_diff": 2.9103830456733704e-11, "charge_rows": 2005, "soc_crossday_max_diff": 0.0, "emergency_event_rows": 5138, "emergency_total_kwh": 853232.2020210004}` |
| result4-3.xlsx | 通过 | `{"file": "result4-3.xlsx", "sheets": ["计划购电量", "调整购电量", "充放电量", "紧急购电量"], "formula_errors": 0, "independent_cost_max_diff": 4.322999757278012e-06, "plan_shape": [335, 147], "max_adjust_diff": 7.275957614183426e-11, "max_adjust_cost_diff": 2.9103830456733704e-11, "max_plan_diff": 7.275957614183426e-11, "max_plan_cost_diff": 7.275957614183426e-12, "charge_rows": 2005, "soc_crossday_max_diff": 0.0, "emergency_event_rows": 5172, "emergency_total_kwh": 1177318.5690499991}` |

## 临时基线警告

当前五个工作簿由`scenario_data/provisional_solution_long.csv`生成，用于验证完整导出链路。该基线严格使用因果预测，但采用零储能动作，`solver_status`含`PROVISIONAL`；不能作为最终竞赛最优结果。优化负责人提交最终`solution_long.csv`后，重新运行导出器和验证器。
