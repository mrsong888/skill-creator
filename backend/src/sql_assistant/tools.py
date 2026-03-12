import json
import logging

from src.sql_assistant.connectors import DBConnector
from src.sql_assistant.safety import check_sql_safety

logger = logging.getLogger(__name__)

SQL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "sql_list_tables",
            "description": "List all available tables in the database. Use this first to discover what data is available.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sql_get_schema",
            "description": (
                "Get the schema (columns, types, sample data) of one or more tables. "
                "Use this to understand table structure before writing SQL queries."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tables": {
                        "type": "string",
                        "description": "Comma-separated table names to inspect (e.g. 'users,orders')",
                    },
                },
                "required": ["tables"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sql_query",
            "description": (
                "Execute a SELECT SQL query against the database. "
                "Only SELECT queries with a LIMIT clause are allowed. "
                "If the query returns an error, analyze the error message, fix the SQL, and retry."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The SELECT SQL query to execute. Must include a LIMIT clause.",
                    },
                },
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sql_validate",
            "description": (
                "Validate SQL syntax before executing. Use this to check for syntax errors, "
                "common mistakes (NULL handling, type mismatches, wrong JOIN conditions), "
                "and engine-specific issues."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The SQL query to validate.",
                    },
                },
                "required": ["sql"],
            },
        },
    },
]


def get_sql_tools() -> list[dict]:
    """Return the SQL tool definitions in OpenAI function format."""
    return list(SQL_TOOLS)


async def execute_sql_tool(name: str, args: dict, connector: DBConnector) -> str:
    """Execute a SQL tool call and return the result as a string."""
    try:
        if name == "sql_list_tables":
            tables = connector.list_tables()
            if not tables:
                return "No tables found in the database."
            return f"Found {len(tables)} tables:\n" + "\n".join(f"  - {t}" for t in tables)

        elif name == "sql_get_schema":
            table_names = [t.strip() for t in args["tables"].split(",") if t.strip()]
            if not table_names:
                return "Error: No table names provided."
            schemas = []
            for table in table_names:
                try:
                    schema = connector.get_table_schema(table)
                    schemas.append(schema)
                except Exception as e:
                    schemas.append(f"Table: {table}\nError: {e}")
            return "\n\n".join(schemas)

        elif name == "sql_query":
            sql = args["sql"]
            # Safety check
            safety_error = check_sql_safety(sql)
            if safety_error:
                return f"Safety check failed: {safety_error}"

            result = connector.execute_query(sql)
            if "error" in result:
                return f"Query error (exec_time: {result['exec_time']}s):\n{result['error']}"

            # Format results
            columns = result["columns"]
            data = result["data"]
            row_count = result["row_count"]
            exec_time = result["exec_time"]

            if not data:
                return f"Query returned 0 rows (exec_time: {exec_time}s)"

            # Build a readable table
            lines = [f"Query returned {row_count} rows (exec_time: {exec_time}s)", ""]
            # Header
            lines.append(" | ".join(str(c) for c in columns))
            lines.append("-" * len(lines[-1]))
            # Data rows (limit display to 50 rows)
            display_rows = data[:50]
            for row in display_rows:
                lines.append(" | ".join(str(v) for v in row))
            if row_count > 50:
                lines.append(f"... ({row_count - 50} more rows)")

            return "\n".join(lines)

        elif name == "sql_validate":
            sql = args["sql"]
            # First: safety check
            safety_error = check_sql_safety(sql)
            if safety_error:
                return f"Safety check failed: {safety_error}"

            # Second: database syntax validation
            db_error = connector.validate_sql(sql)
            if db_error:
                return f"Syntax validation failed:\n{db_error}"

            return "SQL validation passed. The query syntax is correct."

        else:
            return f"Error: Unknown SQL tool: {name}"

    except Exception as e:
        logger.error(f"SQL tool '{name}' execution failed: {e}", exc_info=True)
        return f"Error executing {name}: {e}"
