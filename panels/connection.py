"""connection info panel. shows ips, geo, isp."""
import asyncio
import customtkinter as ctk

from core.engine import engine
from core.cache import cache
from core.config import cfg
from core.logger import get_logger
from utils.network import local_ip
from utils.geo import get_geo

log = get_logger("panel.conn")

class ConnectionPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._build()
        self._load_cached()

    def _build(self):
        ctk.CTkLabel(self, text="Connection Info", font=("Roboto", 18, "bold")).grid(
            row=0, column=0, padx=20, pady=(20,10), sticky="w")

        self.info = ctk.CTkFrame(self, fg_color="transparent")
        self.info.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.info.grid_columnconfigure(1, weight=1)

        self.fields = {}
        rows = [
            ("Public IPv4", "pub_v4"),
            ("Public IPv6", "pub_v6"),
            ("Local IPv4", "loc_v4"),
            ("Local IPv6", "loc_v6"),
            ("Country", "country"),
            ("City", "city"),
            ("ISP", "isp"),
            ("IP Type", "ip_type"),
        ]
        for i, (label, key) in enumerate(rows):
            ctk.CTkLabel(self.info, text=f"{label}:", font=("Roboto", 12, "bold"),
                        text_color=("gray30","gray70")).grid(row=i, column=0, padx=(0,15), pady=3, sticky="w")
            w = ctk.CTkLabel(self.info, text="-", font=("Roboto", 12))
            w.grid(row=i, column=1, pady=3, sticky="w")
            self.fields[key] = w

        self.btn = ctk.CTkButton(self, text="Refresh", command=self._start_refresh,
                                width=100, height=28, font=("Roboto", 11))
        self.btn.grid(row=2, column=0, padx=20, pady=(10,20), sticky="w")

    def _load_cached(self):
        d = cache.get("conn")
        if d:
            self._update(d)

    def _update(self, d: dict):
        for k, w in self.fields.items():
            w.configure(text=str(d.get(k, "-")))

    def _start_refresh(self):
        self.btn.configure(state="disabled", text="...")
        engine.run_in_thread(self._fetch)

    def _fetch(self):
        try:
            data = engine.run(self._async_fetch())
            self.after(0, lambda: self._on_done(data))
        except Exception as e:
            log.error(f"conn fetch failed: {e}")
            self.after(0, lambda: self.btn.configure(state="normal", text="Refresh"))

    async def _async_fetch(self) -> dict:
        t0 = asyncio.get_event_loop().time()
        loc4, loc6 = local_ip()

        client = engine.httpx
        pub4 = pub6 = country = city = region = isp = ""

        try:
            r = await client.get(cfg.cf_trace, timeout=3.0)
            for line in r.text.split("\n"):
                if line.startswith("ip="): pub4 = line[3:]
                elif line.startswith("loc="): country = line[4:]
                elif line.startswith("colo="): isp = line[5:]
        except Exception:
            pass

        try:
            r = await client.get(cfg.cf_trace_v6, timeout=3.0)
            for line in r.text.split("\n"):
                if line.startswith("ip="): pub6 = line[3:]
        except Exception:
            pass

        if not country:
            try:
                g = await get_geo()
                country, city, region, isp = g.country, g.city, g.region, g.isp or isp
                if not pub4: pub4 = g.ip
            except Exception:
                pass

        ip_type = self._guess_type(pub4)

        data = {
            "pub_v4": pub4 or "not detected",
            "pub_v6": pub6 or "not detected",
            "loc_v4": loc4 or "not detected",
            "loc_v6": loc6 or "not detected",
            "country": country or "unknown",
            "city": city or "unknown",
            "isp": isp or "unknown",
            "ip_type": ip_type,
        }
        cache.set("conn", data, ttl=300)
        log.info(f"conn fetched in {(asyncio.get_event_loop().time()-t0)*1000:.0f}ms")
        return data

    def _guess_type(self, ip: str) -> str:
        if not ip:
            return "unknown"
        if ip.startswith(("10.","172.16.","192.168.","127.")):
            return "private"
        cg = tuple(f"100.{i}." for i in range(64, 128))
        if ip.startswith(cg):
            return "vpn/cgnat"
        return "residential"

    def _on_done(self, data: dict):
        self._update(data)
        self.btn.configure(state="normal", text="Refresh")
