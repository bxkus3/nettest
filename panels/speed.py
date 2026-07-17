"""speed & performance. download/upload + multi-target ping."""
import asyncio, time
import customtkinter as ctk

from core.engine import engine
from core.config import cfg
from core.logger import get_logger
from utils.network import ping, PingResult

log = get_logger("panel.speed")

class SpeedPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._build()
        self._running = False

    def _build(self):
        ctk.CTkLabel(self, text="Speed & Performance", font=("Roboto", 18, "bold")).grid(
            row=0, column=0, padx=20, pady=(20,10), sticky="w")

        self.speed_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.speed_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        self.dl = ctk.CTkLabel(self.speed_frame, text="Download: -", font=("Roboto", 15, "bold"))
        self.dl.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.ul = ctk.CTkLabel(self.speed_frame, text="Upload: -", font=("Roboto", 15, "bold"))
        self.ul.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self, text="Latency (ms)", font=("Roboto", 15, "bold")).grid(
            row=2, column=0, padx=20, pady=(20,5), sticky="w")

        self.ping_frame = ctk.CTkScrollableFrame(self, height=180)
        self.ping_frame.grid(row=3, column=0, padx=20, pady=5, sticky="nsew")
        self.ping_frame.grid_columnconfigure(1, weight=1)

        self.ping_widgets = {}
        for i, h in enumerate(cfg.ping_hosts):
            ctk.CTkLabel(self.ping_frame, text=h, font=("Roboto", 11)).grid(row=i, column=0, padx=5, pady=2, sticky="w")
            w = ctk.CTkLabel(self.ping_frame, text="-", font=("Roboto", 11, "bold"))
            w.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            self.ping_widgets[h] = w

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=4, column=0, padx=20, pady=(10,10), sticky="w")

        self.speed_btn = ctk.CTkButton(btns, text="Speed Test", command=self._start_speed,
                                      width=110, height=28, font=("Roboto", 11),
                                      fg_color="#27ae60", hover_color="#219a52")
        self.speed_btn.grid(row=0, column=0, padx=(0,10))

        self.ping_btn = ctk.CTkButton(btns, text="Ping All", command=self._start_ping,
                                     width=110, height=28, font=("Roboto", 11),
                                     fg_color="#2980b9", hover_color="#2471a3")
        self.ping_btn.grid(row=0, column=1)

        self.bar = ctk.CTkProgressBar(self, width=400)
        self.bar.grid(row=5, column=0, padx=20, pady=(0,20), sticky="w")
        self.bar.set(0)

    def _start_speed(self):
        if self._running:
            return
        self._running = True
        self.speed_btn.configure(state="disabled", text="...")
        self.bar.set(0.1)
        engine.run_in_thread(self._run_speed)

    def _run_speed(self):
        try:
            res = engine.run(self._async_speed())
            self.after(0, lambda: self._speed_done(res))
        except Exception as e:
            log.error(f"speed test failed: {e}")
            self.after(0, self._reset_speed)

    async def _async_speed(self) -> dict:
        client = engine.httpx
        total = 0
        t0 = time.perf_counter()

        async def chunk(url):
            nonlocal total
            try:
                r = await client.get(url, timeout=cfg.speed_timeout)
                total += len(r.content)
            except Exception:
                pass

        await asyncio.gather(*[chunk(u) for u in cfg.speed_urls[:3]], return_exceptions=True)
        elapsed = time.perf_counter() - t0
        dl = (total * 8 / 1e6) / elapsed if elapsed > 0 else 0

        ul = 0.0
        try:
            payload = b"X" * 100000
            t1 = time.perf_counter()
            await client.post("https://httpbin.org/post", content=payload, timeout=5.0)
            ul = (len(payload) * 8 / 1e6) / (time.perf_counter() - t1)
        except Exception:
            pass

        return {"dl": round(dl, 2), "ul": round(ul, 2)}

    def _speed_done(self, res: dict):
        self.dl.configure(text=f"Download: {res.get('dl', 0)} Mbps")
        self.ul.configure(text=f"Upload: {res.get('ul', 0)} Mbps")
        self.bar.set(1.0)
        self._reset_speed()

    def _reset_speed(self):
        self._running = False
        self.speed_btn.configure(state="normal", text="Speed Test")

    def _start_ping(self):
        self.ping_btn.configure(state="disabled", text="...")
        engine.run_in_thread(self._run_ping)

    def _run_ping(self):
        try:
            res = engine.run(self._async_ping())
            self.after(0, lambda: self._ping_done(res))
        except Exception as e:
            log.error(f"ping failed: {e}")
            self.after(0, lambda: self.ping_btn.configure(state="normal", text="Ping All"))

    async def _async_ping(self) -> dict:
        import concurrent.futures
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futures = [loop.run_in_executor(pool, ping, h, 3, 2.0) for h in cfg.ping_hosts]
            results = await asyncio.gather(*futures, return_exceptions=True)
        return {h: (r if not isinstance(r, Exception) else PingResult(h, "", loss=100))
                for h, r in zip(cfg.ping_hosts, results)}

    def _ping_done(self, results: dict):
        for host, r in results.items():
            if host in self.ping_widgets:
                txt = f"{r.avg:.1f} ms"
                if r.loss > 0:
                    txt += f" ({r.loss:.0f}% loss)"
                color = "#2ecc71" if r.avg < 50 else ("#f39c12" if r.avg < 150 else "#e74c3c")
                self.ping_widgets[host].configure(text=txt, text_color=color)
        self.ping_btn.configure(state="normal", text="Ping All")
