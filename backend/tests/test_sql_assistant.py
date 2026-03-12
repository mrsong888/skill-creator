"""Tests for the SQL Assistant module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.skill.runtime_config import load_skill_config, save_skill_config
from src.sql_assistant.connectors import ClickHouseConnector, MySQLConnector, PostgreSQLConnector, create_connector
from src.sql_assistant.safety import check_sql_safety
from src.sql_assistant.tools import SQL_TOOLS, execute_sql_tool, get_sql_tools


# --- Connector Factory Tests ---


class TestConnectorFactory:
    def test_create_clickhouse_connector(self):
        connector = create_connector("clickhouse", {
            "host": "localhost",
            "port": 8123,
            "username": "default",
            "password": "",
            "database": "test_db",
        })
        assert isinstance(connector, ClickHouseConnector)
        assert connector.host == "localhost"
        assert connector.port == 8123
        assert connector.database == "test_db"

    def test_create_postgresql_connector(self):
        connector = create_connector("postgresql", {
            "host": "localhost",
            "port": 5432,
            "username": "postgres",
            "password": "secret",
            "database": "mydb",
        })
        assert isinstance(connector, PostgreSQLConnector)
        assert connector.host == "localhost"
        assert connector.port == 5432
        assert connector.database == "mydb"

    def test_create_mysql_connector(self):
        connector = create_connector("mysql", {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "secret",
            "database": "mydb",
        })
        assert isinstance(connector, MySQLConnector)
        assert connector.host == "localhost"
        assert connector.port == 3306
        assert connector.database == "mydb"

    def test_create_connector_case_insensitive(self):
        connector = create_connector("ClickHouse", {"host": "h", "port": 8123})
        assert isinstance(connector, ClickHouseConnector)

        connector = create_connector("PostgreSQL", {"host": "h", "port": 5432})
        assert isinstance(connector, PostgreSQLConnector)

        connector = create_connector("MySQL", {"host": "h", "port": 3306})
        assert isinstance(connector, MySQLConnector)

    def test_create_connector_unsupported_engine(self):
        with pytest.raises(ValueError, match="Unsupported database engine"):
            create_connector("oracle", {"host": "localhost"})

    def test_create_mysql_connector_default_values(self):
        connector = create_connector("mysql", {})
        assert connector.host == "localhost"
        assert connector.port == 3306
        assert connector.username == "root"
        assert connector.password == ""
        assert connector.database == "mysql"

    def test_create_connector_default_values(self):
        connector = create_connector("clickhouse", {})
        assert connector.host == "localhost"
        assert connector.port == 8123
        assert connector.username == "default"
        assert connector.password == ""
        assert connector.database == "default"


# --- SQL Safety Tests ---


class TestSQLSafety:
    def test_safe_select_with_limit(self):
        assert check_sql_safety("SELECT * FROM users LIMIT 10") is None

    def test_safe_cte_with_limit(self):
        assert check_sql_safety("WITH cte AS (SELECT 1) SELECT * FROM cte LIMIT 10") is None

    def test_safe_explain(self):
        assert check_sql_safety("EXPLAIN SELECT * FROM users") is None

    def test_reject_empty_query(self):
        result = check_sql_safety("")
        assert result is not None
        assert "Empty" in result

    def test_reject_insert(self):
        result = check_sql_safety("INSERT INTO users VALUES (1, 'test')")
        assert result is not None
        assert "INSERT" in result

    def test_reject_update(self):
        result = check_sql_safety("UPDATE users SET name='x' WHERE id=1")
        assert result is not None
        assert "UPDATE" in result

    def test_reject_delete(self):
        result = check_sql_safety("DELETE FROM users WHERE id=1")
        assert result is not None
        assert "DELETE" in result

    def test_reject_drop(self):
        result = check_sql_safety("DROP TABLE users")
        assert result is not None
        assert "DROP" in result

    def test_reject_alter(self):
        result = check_sql_safety("ALTER TABLE users ADD COLUMN age INT")
        assert result is not None
        assert "ALTER" in result

    def test_reject_truncate(self):
        result = check_sql_safety("TRUNCATE TABLE users")
        assert result is not None
        assert "TRUNCATE" in result

    def test_reject_select_without_limit(self):
        result = check_sql_safety("SELECT * FROM users")
        assert result is not None
        assert "LIMIT" in result

    def test_reject_non_select(self):
        result = check_sql_safety("SHOW TABLES")
        assert result is not None
        assert "Only SELECT" in result

    def test_strip_comments(self):
        # DML hidden in comment should be safe
        assert check_sql_safety("SELECT 1 -- DELETE FROM users\nLIMIT 1") is None
        # But actual DML after comment stripping should fail
        result = check_sql_safety("/* safe comment */ DELETE FROM users")
        assert result is not None
        assert "DELETE" in result


# --- SQL Tools Tests ---


class TestSQLTools:
    def test_get_sql_tools_returns_list(self):
        tools = get_sql_tools()
        assert isinstance(tools, list)
        assert len(tools) == 4

    def test_sql_tools_have_correct_names(self):
        tools = get_sql_tools()
        names = {t["function"]["name"] for t in tools}
        assert names == {"sql_list_tables", "sql_get_schema", "sql_query", "sql_validate"}

    def test_sql_tools_format(self):
        for tool in SQL_TOOLS:
            assert tool["type"] == "function"
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]


class TestExecuteSQLTool:
    @pytest.fixture
    def mock_connector(self):
        connector = MagicMock()
        connector.list_tables.return_value = ["users", "orders", "products"]
        connector.get_table_schema.return_value = "Table: users\nColumns:\n  - id: Int64\n  - name: String"
        connector.execute_query.return_value = {
            "columns": ["id", "name"],
            "data": [[1, "Alice"], [2, "Bob"]],
            "row_count": 2,
            "exec_time": 0.05,
        }
        connector.validate_sql.return_value = None
        return connector

    async def test_list_tables(self, mock_connector):
        result = await execute_sql_tool("sql_list_tables", {}, mock_connector)
        assert "3 tables" in result
        assert "users" in result
        assert "orders" in result

    async def test_list_tables_empty(self, mock_connector):
        mock_connector.list_tables.return_value = []
        result = await execute_sql_tool("sql_list_tables", {}, mock_connector)
        assert "No tables" in result

    async def test_get_schema(self, mock_connector):
        result = await execute_sql_tool("sql_get_schema", {"tables": "users,orders"}, mock_connector)
        assert mock_connector.get_table_schema.call_count == 2

    async def test_get_schema_empty_tables(self, mock_connector):
        result = await execute_sql_tool("sql_get_schema", {"tables": ""}, mock_connector)
        assert "No table names" in result

    async def test_query_success(self, mock_connector):
        result = await execute_sql_tool("sql_query", {"sql": "SELECT * FROM users LIMIT 10"}, mock_connector)
        assert "2 rows" in result
        assert "Alice" in result
        assert "Bob" in result

    async def test_query_safety_rejected(self, mock_connector):
        result = await execute_sql_tool("sql_query", {"sql": "DELETE FROM users"}, mock_connector)
        assert "Safety check failed" in result
        mock_connector.execute_query.assert_not_called()

    async def test_query_no_limit_rejected(self, mock_connector):
        result = await execute_sql_tool("sql_query", {"sql": "SELECT * FROM users"}, mock_connector)
        assert "Safety check failed" in result
        assert "LIMIT" in result
        mock_connector.execute_query.assert_not_called()

    async def test_query_error(self, mock_connector):
        mock_connector.execute_query.return_value = {"error": "Column not found: foo", "exec_time": 0.01}
        result = await execute_sql_tool("sql_query", {"sql": "SELECT foo FROM users LIMIT 10"}, mock_connector)
        assert "Query error" in result
        assert "Column not found" in result

    async def test_validate_success(self, mock_connector):
        result = await execute_sql_tool("sql_validate", {"sql": "SELECT * FROM users LIMIT 10"}, mock_connector)
        assert "passed" in result

    async def test_validate_syntax_error(self, mock_connector):
        mock_connector.validate_sql.return_value = "Syntax error near 'FORM'"
        result = await execute_sql_tool("sql_validate", {"sql": "SELECT * FORM users LIMIT 10"}, mock_connector)
        assert "Syntax validation failed" in result

    async def test_validate_safety_rejected(self, mock_connector):
        result = await execute_sql_tool("sql_validate", {"sql": "DROP TABLE users"}, mock_connector)
        assert "Safety check failed" in result

    async def test_unknown_tool(self, mock_connector):
        result = await execute_sql_tool("sql_unknown", {}, mock_connector)
        assert "Unknown SQL tool" in result


# --- Runtime Config Tests ---


class TestRuntimeConfig:
    def test_save_and_load_config(self, temp_dir):
        config = {"engine": "clickhouse", "host": "localhost", "port": 8123, "database": "mydb"}
        save_skill_config(temp_dir, config)

        loaded = load_skill_config(temp_dir)
        assert loaded == config

    def test_load_nonexistent_config(self, temp_dir):
        result = load_skill_config(temp_dir / "nonexistent")
        assert result is None

    def test_load_invalid_json(self, temp_dir):
        config_file = temp_dir / "config.json"
        config_file.write_text("not json", encoding="utf-8")
        result = load_skill_config(temp_dir)
        assert result is None

    def test_save_creates_parent_dirs(self, temp_dir):
        nested = temp_dir / "a" / "b" / "c"
        save_skill_config(nested, {"key": "value"})
        assert (nested / "config.json").exists()
        assert load_skill_config(nested) == {"key": "value"}


# --- API Tests ---


class TestSqlAssistantAPI:
    @pytest.fixture
    def mock_connector(self):
        connector = MagicMock()
        connector.test_connection.return_value = (True, "Connected")
        connector.list_tables.return_value = ["users", "orders"]
        return connector

    async def test_test_connection_success(self, mock_connector):
        with patch("src.api.sql_assistant.create_connector", return_value=mock_connector):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/sql/test-connection", json={
                    "engine": "clickhouse",
                    "host": "localhost",
                    "port": 8123,
                    "database": "test_db",
                })
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"
                assert data["table_count"] == 2
                assert "users" in data["tables"]

    async def test_test_connection_failure(self, mock_connector):
        mock_connector.test_connection.return_value = (False, "Connection refused")
        with patch("src.api.sql_assistant.create_connector", return_value=mock_connector):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/sql/test-connection", json={
                    "engine": "clickhouse",
                    "host": "bad-host",
                    "port": 8123,
                    "database": "test_db",
                })
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "error"
                assert "Connection refused" in data["message"]

    async def test_test_connection_unsupported_engine(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/sql/test-connection", json={
                "engine": "oracle",
                "host": "localhost",
                "port": 1521,
                "database": "test",
            })
            assert response.status_code == 400


# --- Template Creation with Config ---


class TestSqlTemplateCreation:
    async def test_create_sql_skill_saves_config(self, temp_dir):
        templates_dir = temp_dir / "templates"
        custom_dir = temp_dir / "custom"
        templates_dir.mkdir()
        custom_dir.mkdir()

        # Copy the sql-assistant template
        import shutil
        src_template = Path(__file__).parent.parent / "skills" / "templates" / "sql-assistant.yaml"
        if src_template.exists():
            shutil.copy(src_template, templates_dir / "sql-assistant.yaml")
        else:
            pytest.skip("sql-assistant.yaml template not found")

        with (
            patch("src.api.skill_templates._get_template_manager") as mock_tm,
            patch("src.api.skill_templates._get_skill_manager") as mock_sm,
        ):
            from src.skill.template_manager import TemplateManager

            tm = TemplateManager(str(templates_dir))
            mock_tm.return_value = tm

            sm = MagicMock()
            sm.custom_path = str(custom_dir)
            mock_sm.return_value = sm

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/skill-templates/sql-assistant/create", json={
                    "variables": {
                        "instance_name": "test-prod",
                        "engine": "ClickHouse",
                        "host": "10.0.0.1",
                        "port": "8123",
                        "db_user": "admin",
                        "db_password": "secret123",
                        "database": "analytics",
                        "business_context": "E-commerce analytics",
                    }
                })
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

                # Verify config.json was saved
                skill_dir = custom_dir / data["skill_name"]
                config = load_skill_config(skill_dir)
                assert config is not None
                assert config["engine"] == "clickhouse"
                assert config["host"] == "10.0.0.1"
                assert config["port"] == 8123
                assert config["username"] == "admin"
                assert config["password"] == "secret123"
                assert config["database"] == "analytics"
