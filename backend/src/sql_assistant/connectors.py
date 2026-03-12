import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DBConnector(ABC):
    """Unified database connection interface."""

    engine: str

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Test the connection. Returns (ok, message_or_error)."""

    @abstractmethod
    def list_tables(self) -> list[str]:
        """List all tables in the database."""

    @abstractmethod
    def get_table_schema(self, table: str) -> str:
        """Return table schema description (columns, types, sample data)."""

    @abstractmethod
    def execute_query(self, sql: str) -> dict:
        """Execute SQL. Returns {columns, data, row_count, exec_time, error?}."""

    @abstractmethod
    def validate_sql(self, sql: str) -> str | None:
        """Validate SQL syntax. None = pass, str = error message."""


class ClickHouseConnector(DBConnector):
    """ClickHouse database connector using clickhouse-connect."""

    engine = "clickhouse"

    def __init__(self, host: str, port: int, username: str = "default", password: str = "", database: str = "default"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self._client = None

    def _get_client(self):
        if self._client is None:
            import clickhouse_connect

            self._client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                database=self.database,
            )
        return self._client

    def test_connection(self) -> tuple[bool, str]:
        try:
            client = self._get_client()
            result = client.query("SELECT 1")
            return True, f"Connected to ClickHouse {self.host}:{self.port}/{self.database}"
        except Exception as e:
            self._client = None
            return False, str(e)

    def list_tables(self) -> list[str]:
        client = self._get_client()
        result = client.query(f"SHOW TABLES FROM {self.database}")
        return [row[0] for row in result.result_rows]

    def get_table_schema(self, table: str) -> str:
        client = self._get_client()
        # Get column definitions
        cols = client.query(f"DESCRIBE TABLE {self.database}.{table}")
        lines = [f"Table: {table}", "Columns:"]
        for row in cols.result_rows:
            col_name, col_type = row[0], row[1]
            default_kind = row[2] if len(row) > 2 else ""
            default_expr = row[3] if len(row) > 3 else ""
            line = f"  - {col_name}: {col_type}"
            if default_kind and default_expr:
                line += f" ({default_kind} {default_expr})"
            lines.append(line)

        # Get sample data (3 rows)
        try:
            sample = client.query(f"SELECT * FROM {self.database}.{table} LIMIT 3")
            if sample.result_rows:
                lines.append("\nSample data (first 3 rows):")
                col_names = [col[0] for col in cols.result_rows]
                for row in sample.result_rows:
                    row_str = ", ".join(f"{col_names[i]}={row[i]}" for i in range(min(len(col_names), len(row))))
                    lines.append(f"  {row_str}")
        except Exception:
            pass

        return "\n".join(lines)

    def execute_query(self, sql: str) -> dict:
        client = self._get_client()
        start = time.time()
        try:
            result = client.query(sql)
            exec_time = round(time.time() - start, 3)
            return {
                "columns": result.column_names,
                "data": [list(row) for row in result.result_rows],
                "row_count": len(result.result_rows),
                "exec_time": exec_time,
            }
        except Exception as e:
            return {"error": str(e), "exec_time": round(time.time() - start, 3)}

    def validate_sql(self, sql: str) -> str | None:
        client = self._get_client()
        try:
            client.query(f"EXPLAIN SYNTAX {sql}")
            return None
        except Exception as e:
            return str(e)


class PostgreSQLConnector(DBConnector):
    """PostgreSQL database connector using psycopg2."""

    engine = "postgresql"

    def __init__(self, host: str, port: int, username: str = "postgres", password: str = "", database: str = "postgres"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self._conn = None

    def _get_conn(self):
        if self._conn is None or self._conn.closed:
            import psycopg2

            self._conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                dbname=self.database,
            )
            self._conn.autocommit = True
        return self._conn

    def test_connection(self) -> tuple[bool, str]:
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True, f"Connected to PostgreSQL {self.host}:{self.port}/{self.database}"
        except Exception as e:
            self._conn = None
            return False, str(e)

    def list_tables(self) -> list[str]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                "ORDER BY table_name"
            )
            return [row[0] for row in cur.fetchall()]

    def get_table_schema(self, table: str) -> str:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name, data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = %s "
                "ORDER BY ordinal_position",
                (table,),
            )
            columns = cur.fetchall()

        lines = [f"Table: {table}", "Columns:"]
        for col_name, data_type, nullable, default in columns:
            line = f"  - {col_name}: {data_type}"
            if nullable == "NO":
                line += " NOT NULL"
            if default:
                line += f" DEFAULT {default}"
            lines.append(line)

        # Sample data
        try:
            with conn.cursor() as cur:
                cur.execute(f'SELECT * FROM "{table}" LIMIT 3')  # noqa: S608
                col_names = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                if rows:
                    lines.append("\nSample data (first 3 rows):")
                    for row in rows:
                        row_str = ", ".join(f"{col_names[i]}={row[i]}" for i in range(len(col_names)))
                        lines.append(f"  {row_str}")
        except Exception:
            pass

        return "\n".join(lines)

    def execute_query(self, sql: str) -> dict:
        conn = self._get_conn()
        start = time.time()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                columns = [desc[0] for desc in cur.description] if cur.description else []
                data = [list(row) for row in cur.fetchall()] if cur.description else []
                exec_time = round(time.time() - start, 3)
                return {
                    "columns": columns,
                    "data": data,
                    "row_count": len(data),
                    "exec_time": exec_time,
                }
        except Exception as e:
            return {"error": str(e), "exec_time": round(time.time() - start, 3)}

    def validate_sql(self, sql: str) -> str | None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"EXPLAIN {sql}")
            return None
        except Exception as e:
            return str(e)


class MySQLConnector(DBConnector):
    """MySQL database connector using PyMySQL."""

    engine = "mysql"

    def __init__(self, host: str, port: int, username: str = "root", password: str = "", database: str = "mysql"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self._conn = None

    def _get_conn(self):
        if self._conn is None or not self._conn.open:
            import pymysql

            self._conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                database=self.database,
                charset="utf8mb4",
                autocommit=True,
            )
        return self._conn

    def test_connection(self) -> tuple[bool, str]:
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True, f"Connected to MySQL {self.host}:{self.port}/{self.database}"
        except Exception as e:
            self._conn = None
            return False, str(e)

    def list_tables(self) -> list[str]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            return [row[0] for row in cur.fetchall()]

    def get_table_schema(self, table: str) -> str:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name, column_type, is_nullable, column_default, column_comment "
                "FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s "
                "ORDER BY ordinal_position",
                (self.database, table),
            )
            columns = cur.fetchall()

        lines = [f"Table: {table}", "Columns:"]
        for col_name, col_type, nullable, default, comment in columns:
            line = f"  - {col_name}: {col_type}"
            if nullable == "NO":
                line += " NOT NULL"
            if default is not None:
                line += f" DEFAULT {default}"
            if comment:
                line += f" -- {comment}"
            lines.append(line)

        # Sample data
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM `{table}` LIMIT 3")  # noqa: S608
                col_names = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                if rows:
                    lines.append("\nSample data (first 3 rows):")
                    for row in rows:
                        row_str = ", ".join(f"{col_names[i]}={row[i]}" for i in range(len(col_names)))
                        lines.append(f"  {row_str}")
        except Exception:
            pass

        return "\n".join(lines)

    def execute_query(self, sql: str) -> dict:
        conn = self._get_conn()
        start = time.time()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                columns = [desc[0] for desc in cur.description] if cur.description else []
                data = [list(row) for row in cur.fetchall()] if cur.description else []
                exec_time = round(time.time() - start, 3)
                return {
                    "columns": columns,
                    "data": data,
                    "row_count": len(data),
                    "exec_time": exec_time,
                }
        except Exception as e:
            return {"error": str(e), "exec_time": round(time.time() - start, 3)}

    def validate_sql(self, sql: str) -> str | None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"EXPLAIN {sql}")
            return None
        except Exception as e:
            return str(e)


def create_connector(engine: str, config: dict) -> DBConnector:
    """Factory method to create a connector based on engine type."""
    engine_lower = engine.lower()
    if engine_lower == "clickhouse":
        return ClickHouseConnector(
            host=config.get("host", "localhost"),
            port=int(config.get("port", 8123)),
            username=config.get("username", "default"),
            password=config.get("password", ""),
            database=config.get("database", "default"),
        )
    elif engine_lower == "postgresql":
        return PostgreSQLConnector(
            host=config.get("host", "localhost"),
            port=int(config.get("port", 5432)),
            username=config.get("username", "postgres"),
            password=config.get("password", ""),
            database=config.get("database", "postgres"),
        )
    elif engine_lower == "mysql":
        return MySQLConnector(
            host=config.get("host", "localhost"),
            port=int(config.get("port", 3306)),
            username=config.get("username", "root"),
            password=config.get("password", ""),
            database=config.get("database", "mysql"),
        )
    else:
        raise ValueError(f"Unsupported database engine: {engine}. Supported: clickhouse, postgresql, mysql")
