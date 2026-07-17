"""async engine. one loop in a background thread.
keeps httpx and aiohttp clients alive."""
import asyncio, threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Coroutine, List
import httpx, aiohttp

from core.config import cfg
from core.logger import get_logger

log = get_logger("engine")

class Engine:
    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._executor = ThreadPoolExecutor(max_workers=cfg.workers, thread_name_prefix="nettest_")
        self._httpx: httpx.AsyncClient | None = None
        self._aio: aiohttp.ClientSession | None = None
        self._sem: asyncio.Semaphore | None = None

    async def _init(self):
        self._sem = asyncio.Semaphore(50)
        if self._httpx is None:
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
            self._httpx = httpx.AsyncClient(
                http2=True, limits=limits,
                timeout=httpx.Timeout(cfg.timeout, connect=2.0),
                follow_redirects=True,
            )
        if self._aio is None:
            conn = aiohttp.TCPConnector(limit=100, limit_per_host=20, ttl_dns_cache=300)
            self._aio = aiohttp.ClientSession(connector=conn, timeout=aiohttp.ClientTimeout(total=cfg.timeout, connect=2.0))

    def start(self):
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_loop, daemon=True, name="async_loop").start()
        asyncio.run_coroutine_threadsafe(self._init(), self._loop).result(timeout=5)
        log.info("engine started")

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro: Coroutine) -> Any:
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=30)

    def run_parallel(self, coros: List[Coroutine]) -> List[Any]:
        async def _gather():
            async with self._sem:
                return await asyncio.gather(*coros, return_exceptions=True)
        fut = asyncio.run_coroutine_threadsafe(_gather(), self._loop)
        return fut.result(timeout=60)

    def run_in_thread(self, fn, *args, **kwargs):
        self._executor.submit(fn, *args, **kwargs)

    @property
    def httpx(self) -> httpx.AsyncClient:
        return self._httpx

    @property
    def aiohttp(self) -> aiohttp.ClientSession:
        return self._aio

    def stop(self):
        if self._loop:
            async def _close():
                if self._httpx: await self._httpx.aclose()
                if self._aio: await self._aio.close()
            try:
                asyncio.run_coroutine_threadsafe(_close(), self._loop).result(timeout=5)
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
        self._executor.shutdown(wait=False)

engine = Engine()
