"""app config. keep it simple."""
from dataclasses import dataclass, field
from typing import List
import os

@dataclass(frozen=True, slots=True)
class Config:
    name: str = "nettest"
    width: int = 1280
    height: int = 800
    theme: str = "dark"

    workers: int = min(32, (os.cpu_count() or 4) * 2)
    timeout: float = 5.0
    speed_timeout: float = 10.0
    cache_ttl: int = 300

    cf_trace: str = "https://1.1.1.1/cdn-cgi/trace"
    cf_trace_v6: str = "https://[2606:4700:4700::1111]/cdn-cgi/trace"
    geo_fallbacks: List[str] = field(default_factory=lambda: [
        "https://ipapi.co/json/",
        "https://ipinfo.io/json",
    ])
    speed_urls: List[str] = field(default_factory=lambda: [
        "https://speed.cloudflare.com/__down?bytes=250000",
        "https://speed.cloudflare.com/__down?bytes=250000",
    ])
    ping_hosts: List[str] = field(default_factory=lambda: [
        "1.1.1.1", "8.8.8.8", "9.9.9.9", "208.67.222.222", "185.228.168.9"
    ])

    vpn_list_url: str = "https://raw.githubusercontent.com/X4BNet/lists_vpn/main/output/datacenter/ipv4.txt"
    tor_list_url: str = "https://check.torproject.org/exit-addresses"

    uas: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    ])

cfg = Config()
