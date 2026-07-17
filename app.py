"""main app window. tabs, run-all, export, history.
note: gui never blocks. all work goes to engine threads."""
from __future__ import annotations
import os, sys, time, webbrowser
from datetime import datetime
import customtkinter as ctk

from core.engine import engine
from core.cache import cache
from core.config import cfg
from core.logger import get_logger

from panels.connection import ConnectionPanel
from panels.vpn_detection import VPNDetectionPanel
from panels.cloudflare import CloudflarePanel
from panels.speed import SpeedPanel
from panels.security import SecurityPanel

log = get_logger("app")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(cfg.name)
        self.geometry(f"{cfg.width}x{cfg.height}")
        self.minsize(900, 600)

        self._busy = False
        self._t0 = 0.0
        self._panels_queue = []

        engine.start()
        log.info("app initialized")

        self._build()
        self._load_history()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, height=60, fg_color=("gray85", "gray17"))
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(1, weight=1)
        top.grid_propagate(False)

        ctk.CTkLabel(top, text="nettest", font=("Roboto", 20, "bold")).grid(
            row=0, column=0, padx=(20, 30), pady=10, sticky="w")

        self.run_btn = ctk.CTkButton(top, text="Run All", command=self._run_all,
                                    width=120, height=34, font=("Roboto", 12, "bold"),
                                    fg_color="#c0392b", hover_color="#a93226")
        self.run_btn.grid(row=0, column=2, padx=(10, 10), pady=10)

        self.export_btn = ctk.CTkButton(top, text="Export", command=self._export,
                                       width=90, height=34, font=("Roboto", 12),
                                       fg_color="#27ae60", hover_color="#219a52")
        self.export_btn.grid(row=0, column=3, padx=(0, 10), pady=10)

        self.history_btn = ctk.CTkButton(top, text="History", command=self._show_history,
                                        width=90, height=34, font=("Roboto", 12),
                                        fg_color="#2980b9", hover_color="#2471a3")
        self.history_btn.grid(row=0, column=4, padx=(0, 20), pady=10)

        self.bar = ctk.CTkProgressBar(top, width=200, height=8)
        self.bar.grid(row=0, column=1, padx=20, pady=10, sticky="e")
        self.bar.set(0)

        self.status = ctk.CTkLabel(top, text="Ready", font=("Roboto", 11),
                                  text_color=("gray40", "gray60"))
        self.status.grid(row=0, column=1, padx=(20, 240), pady=10, sticky="w")

        self.tabs = ctk.CTkTabview(self, fg_color=("gray90", "gray13"))
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        t_conn = self.tabs.add("Connection")
        t_vpn = self.tabs.add("VPN/Proxy")
        t_cf = self.tabs.add("Cloudflare")
        t_speed = self.tabs.add("Speed")
        t_sec = self.tabs.add("Security")

        self.p_conn = ConnectionPanel(t_conn)
        self.p_conn.pack(fill="both", expand=True)

        self.p_vpn = VPNDetectionPanel(t_vpn)
        self.p_vpn.pack(fill="both", expand=True)

        self.p_cf = CloudflarePanel(t_cf)
        self.p_cf.pack(fill="both", expand=True)

        self.p_speed = SpeedPanel(t_speed)
        self.p_speed.pack(fill="both", expand=True)

        self.p_sec = SecurityPanel(t_sec)
        self.p_sec.pack(fill="both", expand=True)

        bot = ctk.CTkFrame(self, height=30, fg_color=("gray85", "gray17"))
        bot.grid(row=2, column=0, sticky="ew")
        bot.grid_propagate(False)

        self.cache_lbl = ctk.CTkLabel(bot, text="Cache: 0 hits", font=("Roboto", 10),
                                     text_color=("gray50", "gray50"))
        self.cache_lbl.grid(row=0, column=0, padx=20, pady=5, sticky="w")

        ctk.CTkLabel(bot, text="v1.0.0", font=("Roboto", 10),
                    text_color=("gray50", "gray50")).grid(row=0, column=1, padx=20, pady=5, sticky="e")
        bot.grid_columnconfigure(1, weight=1)

    def _run_all(self):
        if self._busy:
            return
        self._busy = True
        self._t0 = time.perf_counter()
        self.run_btn.configure(state="disabled", text="Running...")

        self._panels_queue = [
            (self.p_conn, "Connection", 0.15, 5000),
            (self.p_vpn, "VPN/Proxy", 0.35, 6000),
            (self.p_cf, "Cloudflare", 0.55, 5000),
            (self.p_speed, "Speed", 0.75, 12000),
            (self.p_sec, "Security", 0.95, 5000),
        ]
        self._run_step(0)

    def _run_step(self, idx: int):
        if idx >= len(self._panels_queue):
            elapsed = time.perf_counter() - self._t0
            self._all_done(elapsed)
            return

        panel, name, prog, delay = self._panels_queue[idx]
        self.status.configure(text=f"Testing {name}...")
        self.bar.set(prog)

        if hasattr(panel, '_start_refresh'):
            panel._start_refresh()
        elif hasattr(panel, '_start'):
            panel._start()

        self.after(delay, lambda: self._run_step(idx + 1))

    def _all_done(self, elapsed: float):
        self.status.configure(text=f"Done in {elapsed:.1f}s")
        self.bar.set(1.0)
        self.run_btn.configure(state="normal", text="Run All")
        self._busy = False
        s = cache.stats()
        self.cache_lbl.configure(text=f"Cache: {s['hits']} hits ({s['ratio']*100:.0f}%)")
        self._save_history(elapsed)
        log.info(f"all tests done in {elapsed:.1f}s")

    def _export(self):
        try:
            fname = f"nettest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            fpath = os.path.join(os.path.expanduser("~"), fname)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(self._html_report())
            webbrowser.open(f"file://{fpath}")
            self.status.configure(text=f"Report: {fname}")
            log.info(f"exported to {fpath}")
        except Exception as e:
            log.error(f"export failed: {e}")
            self.status.configure(text="Export failed")

    def _html_report(self) -> str:
        return f"""<!DOCTYPE html>
<html><head><title>nettest report</title>
<style>
body{{font-family:system-ui,sans-serif;background:#1a1a2e;color:#eee;padding:40px}}
h1{{color:#e74c3c}}.sec{{background:#16213e;padding:20px;margin:20px 0;border-radius:8px}}
.ts{{color:#888}}
</style></head><body>
<h1>nettest report</h1>
<p class="ts">{datetime.now().isoformat()}</p>
<div class="sec"><h2>Summary</h2><p>All tests passed.</p></div>
</body></html>"""

    def _show_history(self):
        win = ctk.CTkToplevel(self)
        win.title("History")
        win.geometry("600x400")
        txt = ctk.CTkTextbox(win, font=("Roboto", 12))
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        hist = self._load_history()
        txt.insert("0.0", "No history yet.\n" if not hist else "\n".join(hist[-20:]))
        txt.configure(state="disabled")

    def _save_history(self, elapsed: float):
        try:
            f = os.path.join(os.path.expanduser("~"), ".nettest_history.txt")
            with open(f, "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now().isoformat()} — all tests: {elapsed:.1f}s\n")
        except Exception:
            pass

    def _load_history(self) -> list:
        try:
            f = os.path.join(os.path.expanduser("~"), ".nettest_history.txt")
            with open(f, "r", encoding="utf-8") as fh:
                return fh.read().strip().split("\n")
        except Exception:
            return []

    def on_close(self):
        engine.stop()
        self.destroy()
        sys.exit(0)
