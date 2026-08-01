import redis
import hashlib

_redis_client = redis.Redis(host='localhost',port=6379, db=0,decode_responses=True)
CACHE_TTL_SECONDS = 3600  # 1 hour ke baad cache khud expire ho jaaye

def _make_cache_key(question :str) -> str:
    """Question ko normalize karke ek consistent hash-based key banata hai."""
    normalized = question.strip().lower()
    return "query_cache:" + hashlib.sha256(normalized.encode()).hexdigest()

def _get_cached_answer(question: str) -> str |None :
    """Redis se cached answer ko retrieve karta hai."""
    key = _make_cache_key(question)
    return _redis_client.get(key)

def set_cached_answer(question: str, answer: str) -> None:
    key = _make_cache_key(question)
    _redis_client.set(key, answer, ex=CACHE_TTL_SECONDS) #TTL Time to Live set kar diya jaaye, taaki cache automatically expire ho jaaye.

