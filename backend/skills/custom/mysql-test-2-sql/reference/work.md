# Worker Rules

When writing SQL queries:

## General Rules
- Always use `sql_validate` before `sql_query` for complex queries
- Always include a LIMIT clause (default LIMIT 1000)
- Use explicit column names instead of SELECT *
- Use meaningful aliases for computed columns
- Handle NULL values appropriately (COALESCE, nullIf, IFNULL, etc.)
- For division operations, always guard against division by zero
- Use proper date/time functions for the target engine
- When comparing dates, be explicit about timezone handling

## Query Error Recovery
- If a query returns an error, carefully read the error message
- Common issues: column not found, type mismatch, syntax error, ambiguous column
- Fix the SQL and retry, do not ask the user to fix it

## Performance
- Use WHERE clauses to filter data early
- Avoid unnecessary subqueries when JOINs suffice
- For large tables, start with a small LIMIT to verify results before running full queries
