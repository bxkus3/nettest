"""two-tier cache: memory lru + sqlite. 
quick and dirty but works."""
import sqlite3, threading, time
from collections import OrderedDict
from typing import Any, Optional
from contextlib import contextmanager

class Cache:
    def __init__(self, db_path: str = "cache.db", ttl: int = 300, maxsize: int = 256):
        self._mem: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._db = db_path
        self._ttl = ttl
        self._maxsize = maxsize
        self._hits = 0
        self._misses = 0
        self._init_db()

    def _init_db(self):
        with self._db_conn() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value BLOB, expires REAL)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_exp ON cache(expires)")
            conn.commit()

    @contextmanager
    def _db_conn(self):
        conn = sqlite3.connect(self._db, check_same_thread=False, timeout=1.0)
        try:
            yield conn
        finally:
            conn.close()

    def get(self, key: str) -> Optional[Any]:
        now = time.monotonic()
        with self._lock:
            if key in self._mem:
                val, exp = self._mem[key]
                if exp > now:
                    self._mem.move_to_end(key)
                    self._hits += 1
                    return val
                del self._mem[key]
            try:
                with self._db_conn() as conn:
                    row = conn.execute("SELECT value, expires FROM cache WHERE key=?", (key,)).fetchone()
                    if row and row[1] > now:
                        self._mem[key] = (row[0], row[1])
                        self._hits += 1
                        return row[0]
                    elif row:
                        conn.execute("DELETE FROM cache WHERE key=?", (key,))
                        conn.commit()
            except Exception:
                pass
            self._misses += 1
            return None

    def set(self, key: str, val: Any, ttl: Optional[int] = None):
        exp = time.monotonic() + (ttl or self._ttl)
        with self._lock:
            self._mem[key] = (val, exp)
            self._mem.move_to_end(key)
            if len(self._mem) > self._maxsize:
                self._mem.popitem(last=False)
            try:
                with self._db_conn() as conn:
                    conn.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (key, str(val), exp))
                    conn.commit()
            except Exception:
                pass

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {"hits": self._hits, "misses": self._misses, 
                    "ratio": self._hits / total if total else 0.0, "size": len(self._mem)}

cache = Cache()
