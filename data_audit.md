# 数据审计报告

生成时间：2026-09-10T21:50:43（Asia/Shanghai）

## 文件结构

| 文件 | 工作表 | 原始形状 | 日期范围 | 结论 |
|---|---|---:|---|---|
| 附件1.xlsx | Sheet1 | 145×4 | 单日典型曲线 | 144 个十分钟记录 |
| 附件2.xlsx | 小区负载、光伏发电实际功率 | 各 366×145 | 2025-01-01—2025-12-31 | 每日 144 个记录 |
| 附件3.xlsx | Sheet1 | 1461×26 | 2025-01-01—2025-12-31 | 每日 4 次发布、每次 24 个整点提前期 |
| 附件4.xlsx | Sheet1 | 366×145 | 2025-01-01—2025-12-31 | 每日 144 个动态电价 |

## 自动审计结果

```json
{
  "attachment1": {
    "rows": 144,
    "columns": 4,
    "time_labels_unique": 144,
    "first_time_label": "00:10:00",
    "last_time_label": "00:00+1",
    "missing_numeric": 0,
    "negative_numeric": 0,
    "text_numeric_cells": 0,
    "nonnumeric_text_cells": 0
  },
  "attachment2_load": {
    "days": 365,
    "intervals_per_day": 144,
    "date_min": "2025-01-01",
    "date_max": "2025-12-31",
    "missing": 0,
    "negative": 0,
    "min": 1995.7176,
    "max": 7978.8849,
    "q0_1_percent": 2210.8842107,
    "q99_9_percent": 7652.097685599999,
    "duplicate_dates": 0
  },
  "attachment2_pv": {
    "days": 365,
    "intervals_per_day": 144,
    "date_min": "2025-01-01",
    "date_max": "2025-12-31",
    "missing": 0,
    "negative": 0,
    "min": 0.0,
    "max": 10216.2,
    "q0_1_percent": 0.0,
    "q99_9_percent": 9739.216312499999,
    "duplicate_dates": 0
  },
  "attachment4_price": {
    "days": 365,
    "intervals_per_day": 144,
    "date_min": "2025-01-01",
    "date_max": "2025-12-31",
    "missing": 0,
    "negative": 0,
    "min": 0.0076,
    "max": 1.7936,
    "q0_1_percent": 0.1207826,
    "q99_9_percent": 1.7075881999999998,
    "duplicate_dates": 0
  },
  "cell_type_checks": {
    "attachment2_load": {
      "text_numeric_cells": 0,
      "nonnumeric_text_cells": 0
    },
    "attachment2_pv": {
      "text_numeric_cells": 0,
      "nonnumeric_text_cells": 0
    },
    "attachment3": {
      "text_numeric_cells": 0,
      "nonnumeric_text_cells": 1460
    },
    "attachment4_price": {
      "text_numeric_cells": 0,
      "nonnumeric_text_cells": 0
    }
  },
  "source_time_labels": {
    "count": 144,
    "first": "00:10:00",
    "last": "00:00+1",
    "unique": 144
  },
  "attachment3": {
    "rows": 1460,
    "date_min": "2025-01-01",
    "date_max": "2025-12-31",
    "issue_hours": [
      0,
      6,
      12,
      18
    ],
    "dates_not_4_rows": 0,
    "dates_not_4_unique_issues": 0,
    "lead_columns": 24,
    "forecast_missing": 0,
    "forecast_negative": 0,
    "forecast_min_kw": 0.0,
    "forecast_max_kw": 9995.8875,
    "blank_date_cells_expected_ffill": 1095,
    "target_timestamp_min": "2025-01-01 00:10:00",
    "target_timestamp_max": "2026-01-01 18:00:00",
    "targets_in_2026": 220
  }
}
```

## 时间与语义核对

| 类别 | 事实/解释 |
|---|---|
| 题面事实 | 附件 2/4 的列为每日十分钟数据；附件 3 在每日 0:00、6:00、12:00、18:00 发布未来 24 小时整点光伏预测。附件 1 中 `0:00+1` 表示次日 0:00。 |
| 官方模板事实 | 年度模板首个输出列为 `0:10-0:20`，第144个输出列为 `0:00-0:10+1`；result1.xlsx 的第144行写作 `0:00+1-0:10+1`，两者文字不完全一致。 |
| 采用的解释 | 严格遵从团队口径：附件宽表第 t 个数绑定 `interval_index=t`，并写入模板第 t 个位置，不整体平移。附件 3 的“预报 h 小时”按该小时内 6 个十分钟区间的分段常数功率展开。 |
| 敏感性处理 | `scenario_data/official_forecasts_long.csv.gz` 保留发布时刻、提前期、目标时间和十分钟子步，后续可替换为线性插值并复算；当前主结果不做插值。 |

## 质量规则

- 负荷、光伏、价格全部强制转为数值；原始文本数字数量已计入 JSON。
- 负荷与光伏单位为 kW，静态/动态电价单位为元/kWh；十分钟电量换算系数为 1/6。
- 附件 3 的空日期仅是合并展示语义，已向下填充；预测目标跨日、跨年由真实时间戳计算。
- 附件3类型检查中的1460个非数值文本均为`预报时刻`（0:00/6:00/12:00/18:00），不是脏数值。
- 未发现缺失、重复日期/时标、负负荷、负光伏或负电价。报告保留极值及0.1%/99.9%分位数；没有因全局统计“离群”而删除季节性峰值。
- 预测与指标均按时间顺序生成；没有随机打乱，也没有用目标日未来真实值训练。

## 官方论文与支撑材料要求

- 电子版论文建议 PDF，首页必须为摘要专用页，不含承诺书和编号页，文件不超过 20 MB。
- 正文不含目录且不超过 30 页；附录页数不限，必须列出支撑材料文件清单和全部可运行源代码。
- 支撑材料须打包为 RAR/ZIP，不超过 20 MB；不得含参赛者、学校或赛区身份信息。
- 数据、程序、结果与论文数字必须一致，否则存在取消评奖资格风险。

## 已知风险

- GitHub 团队仓库在 2026-09-10 核对时为空；本次仅能采用用户消息中给出的 Q1→Q2→Q3→Q4 主线。
- “调整购电量”字段的绝对量/增量语义题面未以接口字段明示；本管线采用“调整后的绝对计划购电量”，并在交接文档中显式标注。
- 官方模板的显示区间相对附件时间标签存在 10 分钟表面差异；依据用户明确口径按序号一一对应。
- result1.xlsx模板本身没有“全天购电量/全天购电费”列；为满足“不修改宽表表头”，导出器不新增列，相关合计由验证报告从144个区间独立计算。
