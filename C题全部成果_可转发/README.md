# CUMCM 2026 C题交付索引

总负责人先读本文件；建模/论文负责人随后重点阅读 `B_handoff.md`、`model_specification.md` 和 `objective_and_constraints.md`。

锁定主方案：Q1确定性LP；Q2为90%残差分位数安全裕度LP；Q3为0/6/12/18四时刻闭环MPC；Q4-2为净负荷—电价联合场景CVaR；Q4-3为动态电价滚动MPC。Q2的CVaR仅作增强对照。

- `topic_selection_assessment.md`：A/B/C 选题判断与冲国一风险。
- `model_specification.md`：Q1—Q4 模型、数据可得性和控制流程。
- `symbol_table.md`：符号、变量、单位和接口解释。
- `objective_and_constraints.md`：完整目标函数与约束。
- `optimizer_source/`：确定性 LP、调整 LP、两阶段 CVaR-LP 和因果执行器。
- `simulation_source/`：全年仿真、敏感性、官方模板导出与验证代码。
- `solution_long.csv`：五种官方策略的统一长表。
- `daily_metrics.csv`：逐日费用、能量、SOC、残差和求解状态。
- `baseline_results.csv`：无储能、固定规则、点预测、安全裕度、CVaR、MPC 和 Oracle 汇总。
- `sensitivity_results.csv`：物理参数、风险参数、场景数、终端和结算解释敏感性。
- `representative_day_summary.csv`：指定日、最大误差日和最差分位日期结果。
- `solver_log.json`：随机种子、运行时间、状态和最大残差。
- `model_validation_report.md`：硬约束、费用和 Excel 验证。
- `final_consistency_audit.md`：五个官方策略、三张核心 CSV 与官方 Excel 的最终一致性审计。
- `paper_data_handoff.md`：论文负责人可直接引用的结果、统一口径和图表取数指引。
- `A_handoff.md`：数据、预测、场景、接口与五个 Excel 的最终交接。
- `B_handoff.md`：给队友 B/总负责人的最终复现交接。
- `official_results/`：五个已填充并验证的官方结果工作簿及 Excel 验证报告。
- `template_exporter/`：从官方模板重新导出、经桌面版 Excel 重算后复核五个结果文件的独立入口。
- `processed_timeseries.csv`：365天×144区间统一数据长表。
- `forecast_results.csv`、`forecast_metrics.csv`：严格因果预测结果与误差评价。
- `scenario_data/`：残差、完整日轨迹、联合场景和分位数安全裕度。
- `source_inputs/`：题面、附件1—4、官方Excel模板及 `format2026.doc` 论文格式。
- `data_dictionary.md`、`data_audit.md`、`scenario_description.md`：数据口径、审计和场景说明。

`solution_long.csv`、`daily_metrics.csv`、`baseline_results.csv`与五个官方Excel已经完成一致性验证。Oracle仅为完美信息下界，不是可执行策略。
