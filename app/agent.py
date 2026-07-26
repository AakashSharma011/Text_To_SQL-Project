import logging
import os
import re
import time

from dotenv import load_dotenv
from groq import Groq
from sqlalchemy import text

from database import readonly_engine

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

load_dotenv()

MODEL_NAME = "llama-3.3-70b-versatile"
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 10
LLM_TIMEOUT = 30

_BLOCKED_SQL = re.compile(
    r"\b(DROP|DELETE|UPDATE|ALTER|TRUNCATE|INSERT|REPLACE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def _resolve_api_key() -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set in .env")
    return api_key


def _get_schema_info() -> str:
    """Postgres se schema + sample rows padhta hai (information_schema use karke)."""
    schema_parts = []
    with readonly_engine.connect() as conn:
        tables = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )).fetchall()

        for (table,) in tables:
            cols = conn.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = :t"
            ), {"t": table}).fetchall()

            schema_parts.append(f"-- Table: {table}")
            for col_name, data_type in cols:
                schema_parts.append(f"--   {col_name} ({data_type})")

            rows = conn.execute(text(f"SELECT * FROM {table} LIMIT 3")).fetchall()
            schema_parts.append(f"-- Sample rows:")
            for row in rows:
                schema_parts.append(f"--   {row}")
            schema_parts.append("")

    return "\n".join(schema_parts)


def _validate_query_safety(query: str) -> str | None:
    match = _BLOCKED_SQL.search(query)
    if match:
        keyword = match.group(0).upper()
        return f"⚠️ Blocked: This would need a **{keyword}** operation. Only SELECT queries are allowed."
    return None


def _validate_input(user_input: str) -> str | None:
    stripped = user_input.strip()
    if not stripped:
        return "Please enter a question about your business data."
    if len(stripped) < 3:
        return "Your question is too short."
    if len(stripped) > 1000:
        return "Your question is too long (max 1000 characters)."
    return None


def _is_rate_limit_error(error: Exception) -> bool:
    msg = str(error).lower()
    return any(kw in msg for kw in ["rate limit", "quota", "429", "resource exhausted", "too many requests"])


def _extract_sql(text_response: str) -> str:
    sql_match = re.search(r"```(?:sql)?\s*\n?(.*?)\n?```", text_response, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()
    select_match = re.search(r"(SELECT\s+.+?)(?:;|$)", text_response, re.DOTALL | re.IGNORECASE)
    if select_match:
        return select_match.group(1).strip()
    return text_response.strip()


def _call_llm_with_retry(client: Groq, prompt: str) -> str:
    backoff = INITIAL_BACKOFF_SECONDS
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=1024,
                timeout=LLM_TIMEOUT,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_error = e
            if _is_rate_limit_error(e) and attempt < MAX_RETRIES:
                logger.warning(f"Rate limit (attempt {attempt}/{MAX_RETRIES}). Waiting {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
    raise last_error


class SQLAgent:
    def __init__(self) -> None:
        self._client = None
        self._schema = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        api_key = _resolve_api_key()
        self._client = Groq(api_key=api_key)
        self._schema = _get_schema_info()
        self._initialized = True
        logger.info("SQL Agent initialized.")

    def query(self, user_question: str) -> str:
        input_error = _validate_input(user_question)
        if input_error:
            return input_error

        try:
            self._ensure_initialized()
        except Exception as e:
            logger.error(f"Init failed: {e}")
            return f"❌ Failed to initialize: {e}"

        try:
            sql_prompt = f"""You are a PostgreSQL expert. Given this schema:

{self._schema}

Write a SQL SELECT query to answer: "{user_question}"

Rules:
- Only SELECT queries, never modify data.
- Always add LIMIT 100 unless a specific count is asked.
- Return ONLY the SQL query, no explanation.
- Use proper PostgreSQL syntax.
"""
            sql_response = _call_llm_with_retry(self._client, sql_prompt)
            sql_query = _extract_sql(sql_response)

            safety_check = _validate_query_safety(sql_query)
            if safety_check:
                return safety_check

            if "LIMIT" not in sql_query.upper():
                sql_query = sql_query.rstrip(";").strip() + " LIMIT 100"

            logger.info(f"Generated SQL: {sql_query}")

        except Exception as e:
            if _is_rate_limit_error(e):
                return "⏳ Rate limit reached. Please wait and try again."
            logger.error(f"SQL generation error: {e}")
            return f"❌ Error generating query: {e}"

        try:
            with readonly_engine.connect() as conn:
                result = conn.execute(text(sql_query))
                columns = list(result.keys())
                rows = result.fetchall()

            if not rows:
                return "📭 No results found. Try rephrasing."

            result_text = f"Columns: {', '.join(columns)}\n"
            for row in rows[:50]:
                result_text += f"  {row}\n"
            if len(rows) > 50:
                result_text += f"  ... and {len(rows) - 50} more rows\n"

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return f"❌ Database error: {e}. Try rephrasing your question."

        try:
            answer_prompt = f"""Based on this SQL query and results, give a clear English answer.

Question: "{user_question}"
SQL: {sql_query}
Results:
{result_text}

Rules:
- Clear, friendly English for a non-technical user.
- Include specific numbers.
- Do NOT mention SQL.
"""
            return _call_llm_with_retry(self._client, answer_prompt)
        except Exception as e:
            logger.error(f"Answer generation error: {e}")
            return f"❌ Error generating answer: {e}"


_agent_instance = SQLAgent()


def query_agent(question: str) -> str:
    return _agent_instance.query(question)
