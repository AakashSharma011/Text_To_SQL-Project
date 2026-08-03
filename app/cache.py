import os
import hashlib
import logging
from upstash_redis import Redis

logger = logging.getLogger(__name__)

_redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
_redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

_redis_client = None
if _redis_url and _redis_token:
    try:
        _redis_client = Redis(url=_redis_url, token=_redis_token)
        logger.info("Initialized Upstash REST Redis client successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Upstash Redis client: {e}")
        _redis_client = None
else:
    logger.warning("UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN not configured. Caching is disabled.")

CACHE_TTL_SECONDS = 3600


def _make_cache_key(question: str) -> str:
    normalized = question.strip().lower()
    return "query_cache:" + hashlib.sha256(normalized.encode()).hexdigest()


def get_cached_answer(question: str) -> str | None:
    if not _redis_client:
        return None
    try:
        key = _make_cache_key(question)
        res = _redis_client.get(key)
        if res:
            logger.info(f"Upstash Redis cache hit for key: {key[:15]}...")
        return res
    except Exception as e:
        logger.error(f"Error fetching from Upstash Redis: {e}")
        return None  # Redis down ho to bhi app crash na ho, cache bina bhi chal jaaye


def set_cached_answer(question: str, answer: str) -> None:
    if not _redis_client:
        return
    try:
        key = _make_cache_key(question)
        _redis_client.set(key, answer, ex=CACHE_TTL_SECONDS)
        logger.info(f"Upstash Redis cache set for key: {key[:15]}...")
    except Exception as e:
        logger.error(f"Error setting Upstash Redis cache: {e}")
        pass  # cache save fail ho to bhi silently ignore, poora request fail na ho