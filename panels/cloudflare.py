"""cloudflare & waf detection. checks cdn-cgi trace, blocks, challenges."""
import asyncio, random
import customtkinter as ctk

from core.engine import engine
from core.config import cfg
from core.logger import get_logger

log = get_logger("panel.cf")

class CloudflarePanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Cloudflare & WAF Detection", font=("Roboto", 18, "bold")).grid(
            row=0, column=0, padx=20, pady=(20,10), sticky="w")

        self.results = ctk.CTkFrame(self, fg_color="transparent")
        self.results.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.results.grid_columnconfigure(1, weight=1)

        self.checks = {}
        rows = [
            ("Cloudflare Connected", "cf_conn"),
            ("CDN-CGI Trace", "trace"),
            ("WAF Active", "waf"),
            ("Bot Fight Mode", "bot"),
            ("Challenge Page", "challenge"),
            ("Block 1020", "b1020"),
            ("Block 1015", "b1015"),
            ("Ray ID Present", "ray"),
        ]
        for i, (label, key) in enumerate(rows):
            ctk.CTkLabel(self.results, text=f"{label}:", font=("Roboto", 12, "bold"),
                        text_color=("gray30","gray70")).grid(row=i, column=0, padx=(0,15), pady=3, sticky="w")
            w = ctk.CTkLabel(self.results, text="-", font=("Roboto", 12))
            w.grid(row=i, column=1, pady=3, sticky="w")
            self.checks[key] = w

        self.btn = ctk.CTkButton(self, text="Test Cloudflare", command=self._start,
                                width=120, height=28, font=("Roboto", 11),
                                fg_color="#d68910", hover_color="#b9770e")
        self.btn.grid(row=2, column=0, padx=20, pady=(10,20), sticky="w")

    def _start(self):
        self.btn.configure(state="disabled", text="testing...")
        engine.run_in_thread(self._run)

    def _run(self):
        try:
            res = engine.run(self._async_test())
            self.after(0, lambda: self._show(res))
        except Exception as e:
            log.error(f"cf test failed: {e}")
            self.after(0, lambda: self.btn.configure(state="normal", text="Test Cloudflare"))

    async def _async_test(self) -> dict:
        t0 = asyncio.get_event_loop().time()
        client = engine.httpx

        cf = {}
        try:
            r = await client.get("https://1.1.1.1/cdn-cgi/trace", timeout=4.0)
            for line in r.text.split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    cf[k] = v
        except Exception:
            pass

        codes = []
        for ua in [random.choice(cfg.uas), "curl/7.68.0", "Mozilla/5.0 (compatible; Bot/0.1)"]:
            try:
                r = await client.get("https://httpbin.org/get", headers={"User-Agent": ua}, timeout=3.0)
                codes.append(r.status_code)
            except Exception as e:
                s = str(e)
                codes.append(403 if "403" in s or "1020" in s else (429 if "1015" in s else 0))

        has_403 = 403 in codes
        has_429 = 429 in codes

        out = {
            "cf_conn": "yes" if cf.get("ip") else "no",
            "trace": cf.get("loc", "ok") if cf else "failed",
            "waf": "possible" if has_403 else "no",
            "bot": "active" if has_403 else "inactive",
            "challenge": "yes" if has_403 else "no",
            "b1020": "blocked" if has_403 else "clear",
            "b1015": "rate-limited" if has_429 else "clear",
            "ray": "yes" if cf.get("ts") else "no",
        }
        log.info(f"cf test done in {(asyncio.get_event_loop().time()-t0)*1000:.0f}ms")
        return out

    def _show(self, data: dict):
        for k, w in self.checks.items():
            if k in data:
                w.configure(text=str(data[k]))
        self.btn.configure(state="normal", text="Test Cloudflare")
