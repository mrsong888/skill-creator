# Worker Rules

SQL 编写与执行阶段的规则。包括 text2sql 转换、查询模式选择和错误恢复。

## 通用 SQL 编写规则

- 执行复杂查询前，始终使用 `sql_validate` 验证。
- 始终包含 `LIMIT` 子句（默认 `LIMIT 1000`）。
- 使用明确的列名，不用 `SELECT *`。
- 为计算列使用有意义的别名（如 `COUNT(*) AS order_count`）。
- 适当处理 NULL 值（`COALESCE`、`NULLIF`、`IFNULL` 等）。
- 除法运算必须防止除以零（`x / NULLIF(y, 0)`）。
- 使用 MySQL 的日期/时间函数（`DATE()`、`DATE_FORMAT()`、`NOW()`、`CURDATE()`、`TIMESTAMPDIFF()` 等）。
- 日期比较时明确时区处理。

## Text2SQL 查询模式选择

根据用户需求选择合适的 SQL 模式：

| 用户需求 | SQL 模式 |
|---|---|
| 总数、平均值、计数 | `GROUP BY` + 聚合函数 |
| Top N / Bottom N | `ORDER BY metric DESC/ASC LIMIT N` |
| 时间趋势 | `GROUP BY DATE()/DATE_FORMAT()` + `ORDER BY date` |
| 分组对比 | `GROUP BY category` 或 `CASE WHEN` 透视 |
| 占比/百分比 | 窗口函数 `SUM() OVER()` 或子查询求总数 |
| 同比/环比 | 自连接或 CTE + 日期偏移过滤 |
| 存在性检查 | `EXISTS` / `IN` 子查询 或 `LEFT JOIN ... IS NULL` |
| 累计值 | 窗口函数 `SUM() OVER (ORDER BY ...)` |
| 去重 | `GROUP BY` 或 `ROW_NUMBER() OVER (PARTITION BY ...)` |
| 漏斗/顺序事件 | 多个 CTE + 逐步过滤 |

## CTE 与子查询选择

- 多步逻辑优先使用 CTE（`WITH ... AS`），可读性更好。
- 简单的单次引用可以用子查询。
- 需要多次引用同一中间结果时，必须用 CTE。

## JOIN 编写规则

- 明确使用 `INNER JOIN`、`LEFT JOIN`、`RIGHT JOIN`，不要用隐式 JOIN（逗号分隔表名）。
- JOIN 条件写在 `ON` 子句中，过滤条件写在 `WHERE` 子句中。
- 多表 JOIN 时，注意是否会产生笛卡尔积或重复行。
- 如果只需要检查存在性，用 `EXISTS` 比 `JOIN` 更高效。

## 性能注意事项

- 使用 `WHERE` 子句尽早过滤数据。
- 当 `JOIN` 能解决问题时，避免不必要的子查询。
- 对大表先用小 `LIMIT` 验证结果正确性，再执行完整查询。
- 避免在 `WHERE` 子句中对列使用函数（如 `WHERE YEAR(date_col) = 2024`），这会阻止索引使用。改用范围条件（如 `WHERE date_col >= '2024-01-01' AND date_col < '2025-01-01'`）。

## 查询错误恢复

- 如果查询返回错误，仔细阅读错误信息。
- 常见错误及修复方式：

| 错误类型 | 常见原因 | 修复方法 |
|---|---|---|
| Column not found | 列名拼写错误或不存在 | 重新检查 schema |
| Ambiguous column | 多表 JOIN 中列名冲突 | 添加表别名前缀 |
| Type mismatch | 数据类型不匹配 | 使用 `CAST()` 或 `CONVERT()` |
| Syntax error | SQL 语法错误 | 检查关键字、括号、逗号 |
| Subquery returns more than 1 row | 子查询用在需要标量的位置 | 添加 `LIMIT 1` 或改用 `IN` |
| Division by zero | 除数为零 | 使用 `NULLIF(denominator, 0)` |

- 自行修复错误并重试，不要让用户修复 SQL。
- 连续 3 次相同查询失败后，向用户解释问题而不是继续重试。