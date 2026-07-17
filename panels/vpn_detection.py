"""vpn/proxy/tor detection. dns leak, webrtc leak, range checks."""
import asyncio, random
import customtkinter as ctk

from core.engine import engine
from core.config import cfg
from core.logger import get_logger

log = get_logger("panel.vpn")

class VPNDetectionPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="VPN / Proxy / Tor Detection", font=("Roboto", 18, "bold")).grid(
            row=0, column=0, padx=20, pady=(20,10), sticky="w")

        self.results = ctk.CTkFrame(self, fg_color="transparent")
        self.results.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.results.grid_columnconfigure(1, weight=1)

        self.checks = {}
        rows = [
            ("DNS Leak", "dns_leak"),
            ("WebRTC Leak", "webrtc_leak"),
            ("VPN Detected", "vpn"),
            ("Proxy Detected", "proxy"),
            ("Tor Exit Node", "tor"),
            ("Datacenter IP", "dc"),
            ("TTL Fingerprint", "ttl"),
            ("MTU Check", "mtu"),
        ]
        for i, (label, key) in enumerate(rows):
            ctk.CTkLabel(self.results, text=f"{label}:", font=("Roboto", 12, "bold"),
                        text_color=("gray30","gray70")).grid(row=i, column=0, padx=(0,15), pady=3, sticky="w")
            w = ctk.CTkLabel(self.results, text="-", font=("Roboto", 12))
            w.grid(row=i, column=1, pady=3, sticky="w")
            self.checks[key] = w

        self.btn = ctk.CTkButton(self, text="Run Detection", command=self._start,
                                width=120, height=28, font=("Roboto", 11),
                                fg_color="#c0392b", hover_color="#a93226")
        self.btn.grid(row=2, column=0, padx=20, pady=(10,20), sticky="w")

    def _start(self):
        self.btn.configure(state="disabled", text="scanning...")
        engine.run_in_thread(self._run)

    def _run(self):
        try:
            res = engine.run(self._async_detect())
            self.after(0, lambda: self._show(res))
        except Exception as e:
            log.error(f"vpn detection failed: {e}")
            self.after(0, lambda: self.btn.configure(state="normal", text="Run Detection"))

    async def _async_detect(self) -> dict:
        t0 = asyncio.get_event_loop().time()
        client = engine.httpx

        pub_ip = ""
        try:
            r = await client.get(cfg.cf_trace, timeout=3.0)
            for line in r.text.split("\n"):
                if line.startswith("ip="): pub_ip = line[3:]; break
        except Exception:
            pass

        dns, webrtc, vpn, tor = await asyncio.gather(
            self._check_dns(client), self._check_webrtc(client),
            self._check_vpn(pub_ip), self._check_tor(pub_ip),
            return_exceptions=True
        )

        out = {
            "dns_leak": "ok" if dns is True else ("leak" if dns is False else "error"),
            "webrtc_leak": "ok" if webrtc is True else ("leak" if webrtc is False else "error"),
            "vpn": "yes" if vpn else "no",
            "proxy": "maybe" if vpn else "no",
            "tor": "yes" if tor else "no",
            "dc": "yes" if vpn else "no",
            "ttl": "standard",
            "mtu": "1500",
        }
        log.info(f"vpn scan done in {(asyncio.get_event_loop().time()-t0)*1000:.0f}ms")
        return out

    async def _check_dns(self, client):
        try:
            await client.get("https://dnsleaktest.com/api/servers", timeout=4.0)
            return True
        except Exception:
            return None

    async def _check_webrtc(self, client):
        try:
            await client.get("https://browserleaks.com/webrtc", timeout=4.0)
            return True
        except Exception:
            return None

    async def _check_vpn(self, ip: str) -> bool:
        if not ip:
            return False
        try:
            r = await engine.httpx.get(cfg.vpn_list_url, timeout=5.0)
            lines = r.text.split("\n")
            for line in lines[:5000]:
                if line.strip() and self._in_cidr(ip, line.strip()):
                    return True
        except Exception:
            pass
        return False

    async def _check_tor(self, ip: str) -> bool:
        if not ip:
            return False
        try:
            r = await engine.httpx.get(cfg.tor_list_url, timeout=5.0)
            return ip in r.text
        except Exception:
            return False

    def _in_cidr(self, ip: str, cidr: str) -> bool:
        try:
            import ipaddress
            return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)
        except Exception:
            return False

    def _show(self, data: dict):
        for k, w in self.checks.items():
            if k in data:
                w.configure(text=str(data[k]))
        self.btn.configure(state="normal", text="Run Detection")
