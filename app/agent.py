import logging
import os
import time
import re
from database import readonly_engine
from sqlalchemy import text
from groq import Groq
from dotenv import load_dotenv

logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

load_dotenv()

MODEL_NAME ="llama-3.3-70b-versatile"
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 10 # Initial backoff time in seconds
LLM_TIMEOUT=30

_BLOCKED_SQL = re.compile(r"(?i)\b(ALTER|CREATE|DROP|DELETE|INSERT|UPDATE|TRUNCATE|REPLACE)\b",
re.IGNORECASE)

def _resolve_api_key() -> str:
    api_key=os.getenv("GROQ_API_KEY","").strip()
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY environment variable is not set or is empty.")
    return api_key


def _get_schema_info() -> str:
    """Postgres se schema + sample rows padhta hai (information_schema use karke)."""
    schema_parts=[]
    with readonly_engine.connect() as conn:
        tables= conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public")).fetchall()
        for (table,) in tables:
            cols = conn.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = :t"
            ), {"t": table}).fetchall()
            schema_parts.append(f"-- Table:{table}")
            for col_name,data_type in cols:
                schema_parts.append(f"-- Column:{col_name} {data_type}")
                row= conn.execute(text(f"SELECT * FROM {table} LIMIT 3")).fetchall()
                schema_parts.append(f"-- Sample rows")
                for row in row:
                    schema_parts.append(f"--  {row}")
                schema_parts.append(" ")
    return "/n".join(schema_parts)


def _validate_query_safety(query:str)->str|None:
    match=_BLOCKED_SQL.search(query)
    if match:
        keywords=match.group(0).upper()
        return f"Query contains blocked SQL keywords: {keywords}. Only SELECT queries are allowed."
    return None


def _validate_input(user_input:str)->str|None:
    stripped=user_input.strip()
    if not stripped:
        return "Input is empty. Please provide a Query."
    if len(stripped) < 3:
        return "Your question is too short."
    if len(stripped) > 1000:
        return "Your question is too long (max 1000 characters)."
    return None

def _is_rate_limited_error(error:Exception)->bool:
    msg=str(error).lower()
    return any(kw in msg for kw in["rate limit", "quota", "429", "resource exhausted", "too many requests"])

def _extract_sql(text_response:str)->str:
    sql_match = re.search(r"```(?:sql)?\s*\n?(.*?)\n?```", text_response, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()
    select_match = re.search(r"(SELECT\s+.+?)(?:;|$)", text_response, re.DOTALL | re.IGNORECASE)
    if select_match:
        return select_match.group(1).strip()
    return text_response.strip()






        



