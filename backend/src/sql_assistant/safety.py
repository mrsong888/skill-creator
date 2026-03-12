import re

# DML/DDL keywords that are not allowed
FORBIDDEN_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "REPLACE",
    "MERGE",
    "GRANT",
    "REVOKE",
    "RENAME",
]

# Pattern to match forbidden keywords at word boundaries (case-insensitive)
_FORBIDDEN_PATTERN = re.compile(r"\b(" + "|".join(FORBIDDEN_KEYWORDS) + r")\b", re.IGNORECASE)

# Pattern to detect LIMIT clause
_LIMIT_PATTERN = re.compile(r"\bLIMIT\s+\d+", re.IGNORECASE)


def _strip_comments(sql: str) -> str:
    """Remove SQL comments (single-line and multi-line)."""
    # Remove single-line comments
    sql = re.sub(r"--[^\n]*", "", sql)
    # Remove multi-line comments
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql


def check_sql_safety(sql: str) -> str | None:
    """
    Check SQL for safety violations.
    Returns None if safe, or an error message string if unsafe.
    """
    cleaned = _strip_comments(sql).strip()

    if not cleaned:
        return "Empty SQL query"

    # Check for forbidden DML/DDL keywords
    match = _FORBIDDEN_PATTERN.search(cleaned)
    if match:
        keyword = match.group(1).upper()
        return f"Forbidden operation: {keyword}. Only SELECT queries are allowed."

    # Check that query starts with SELECT (or WITH for CTEs)
    first_word = cleaned.split()[0].upper()
    if first_word not in ("SELECT", "WITH", "EXPLAIN"):
        return f"Only SELECT queries are allowed. Got: {first_word}"

    # Check for LIMIT clause (required for safety)
    if first_word != "EXPLAIN" and not _LIMIT_PATTERN.search(cleaned):
        return "Query must include a LIMIT clause to prevent unbounded result sets."

    return None
