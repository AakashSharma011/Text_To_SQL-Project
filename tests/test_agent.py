from unittest.mock import MagicMock
from app.agent import _call_llm_with_retry
from app.agent import  _validate_query_safety ,SQLAgent

def test_block_drop_statement():
    dangerous_sql = "DROP TABLE users;"
    result = _validate_query_safety(dangerous_sql)
    assert result is not None
    assert "Blocked" in result

def test_blocks_delete_statement():
    dangerous_sql = "DELETE FROM employees WHERE id = 1;"
    result = _validate_query_safety(dangerous_sql)
    assert result is not None
    assert "Blocked" in result

def test_allows_select_statement():
    safe_sql = "SELECT * FROM employees LIMIT 10;"
    result = _validate_query_safety(safe_sql)
    assert result is None 

from unittest.mock import MagicMock
from app.agent import _call_llm_with_retry


def test_call_llm_returns_response_content(mocker):
    # Arrange — ek fake Groq client banao jo fixed response de
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices[0].message.content = "  SELECT * FROM employees;  "
    fake_client.chat.completions.create.return_value = fake_response

    # Act
    result = _call_llm_with_retry(fake_client, "DELETE FROM employees;")  # koi bhi prompt chalega, kyunki humne response mock kiya hai

    # Assert
    assert result == "SELECT * FROM employees;"  # .strip() ho ke aana chahiye


def test_call_llm_retries_on_rate_limit(mocker):
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices[0].message.content="SELECT 1;"
    fake_client.chat.completions.create.side_effect=[
        Exception("429 rate limit exceeded"),  # 1st call — fail
        fake_response,                          # 2nd call — success
    ]
    mocker.patch("app.agent.time.sleep")
    # Act
    result = _call_llm_with_retry(fake_client, "koi prompt")

    # Assert
    assert result == "SELECT 1;"
    assert fake_client.chat.completions.create.call_count == 2 


def test_execute_sql_succeeds_first_try(mocker):
    # Arrange
    agent = SQLAgent()
    agent._client = MagicMock()  # correction call ke liye chahiye hoga, abhi use nahi hoga
    agent._schema = "-- fake schema"

    fake_conn = MagicMock()
    fake_result = MagicMock()
    fake_result.keys.return_value = ["id", "name"]
    fake_result.fetchall.return_value = [(1, "Aarav"), (2, "Priya")]
    fake_conn.execute.return_value = fake_result

    # readonly_engine.connect() ek context manager return karta hai (with ... as conn)
    mock_engine_connect = MagicMock()
    mock_engine_connect.__enter__.return_value = fake_conn
    mocker.patch("app.agent.readonly_engine.connect", return_value=mock_engine_connect)

    # Act
    sql, result, error = agent._execute_sql_with_correction("SELECT * FROM employees;", "list employees")

    # Assert
    assert error is None
    assert sql == "SELECT * FROM employees;"
    columns, rows = result
    assert columns == ["id", "name"]
    assert rows == [(1, "Aarav"), (2, "Priya")]


def test_execute_sql_corrects_after_failure(mocker):
    agent = SQLAgent()
    agent._client = MagicMock()
    agent._schema = "-- fake schema"

    # Success wala fake connection
    fake_conn = MagicMock()
    fake_result = MagicMock()
    fake_result.keys.return_value = ["id", "name"]
    fake_result.fetchall.return_value = [(1, "Aarav"), (2, "Priya")]
    fake_conn.execute.return_value = fake_result

    mock_engine_connect = MagicMock()
    mock_engine_connect.__enter__.return_value = fake_conn

    # Pehli call fail (Exception), doosri call success (mock_engine_connect)
    mocker.patch(
        "app.agent.readonly_engine.connect",
        side_effect=[Exception("relation \"wrong_table\" does not exist"), mock_engine_connect],
    )

    # Correction call — LLM ek fixed corrected SQL deta hai
    mocker.patch("app.agent._call_llm_with_retry", return_value="SELECT * FROM employees;")

    # Act
    sql, result, error = agent._execute_sql_with_correction("SELECT * FROM wrong_table;", "kuch sawaal")

    # Assert
    assert error is None
    assert sql == "SELECT * FROM employees"
    columns, rows = result
    assert columns == ["id", "name"]
    assert rows == [(1, "Aarav"), (2, "Priya")]