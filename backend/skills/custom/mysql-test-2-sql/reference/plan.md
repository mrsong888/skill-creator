# Plan Rules

When the user asks a data question, follow these steps:

1. **Understand the question**: Identify what metrics, dimensions, and filters are needed.
2. **Discover tables**: Use `sql_list_tables` to see available tables if you haven't already.
3. **Inspect schema**: Use `sql_get_schema` to understand relevant table structures.
4. **Break down complex queries**: For multi-step analysis, plan the query sequence:
   - Start with simpler queries to validate assumptions
   - Build up to the final query
5. **Consider edge cases**: NULL values, timezone handling, data type conversions.
