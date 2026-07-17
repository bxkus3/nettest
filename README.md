# nettest

A fast desktop network diagnostics tool built with Python and CustomTkinter. Runs all tests asynchronously so the UI never freezes.

## What it does

- **Connection Info** -- Public/local IPv4 and IPv6, geolocation, ISP detection, IP type classification
- **VPN / Proxy / Tor Detection** -- DNS leak test, WebRTC leak test, checks against known VPN/datacenter ranges and Tor exit nodes
- **Cloudflare & WAF Detection** -- CDN connectivity, WAF status, bot fight mode, block code detection (1020/1015)
- **Speed & Performance** -- Download/upload speed test via Cloudflare, parallel ping to multiple hosts with jitter and packet loss
- **Security & Privacy** -- TLS version detection, header analysis, browser fingerprint scoring, privacy score 0-100

## Architecture

The GUI runs on the main thread and never blocks. All network I/O goes through a background asyncio event loop with connection pooling (httpx + aiohttp). CPU-bound work like ICMP ping runs in a ThreadPoolExecutor. Results are cached in-memory (LRU) with SQLite persistence.

## Requirements

- Python 3.11+
- Windows, Linux, or macOS

## Install and run

```bash
git clone https://github.com/YOUR_USERNAME/nettest.git
cd nettest
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

## Build standalone .exe (Windows)

Install PyInstaller:

```bash
pip install pyinstaller
```

Build:

```bash
pyinstaller nettest.spec --clean --noconfirm
```

The executable will be at `dist/nettest.exe`.

If you need to debug build issues, temporarily change `--windowed` to `--console` in `nettest.spec` to see stderr output.

## Usage

1. Launch the app.
2. Click any panel's action button (e.g. "Refresh", "Run Detection") to run tests for that category.
3. Click **Run All** in the top bar to execute every test sequentially. The progress bar and status label show what's happening.
4. Click **Export** to generate an HTML report of the current session.
5. Click **History** to view past test runs.

Individual panels can be refreshed independently without affecting others.

## Project structure

```
nettest/
├── main.py              # Entry point
├── app.py               # Main window, tab controller, run-all logic
├── nettest.spec         # PyInstaller spec
├── requirements.txt     # Dependencies
├── core/
│   ├── config.py        # Immutable app configuration
│   ├── logger.py        # Rich-based structured logging
│   ├── cache.py         # Two-tier cache (in-memory LRU + SQLite)
│   └── engine.py        # Async event loop + thread pool
├── panels/
│   ├── connection.py    # IP and geolocation panel
│   ├── vpn_detection.py # VPN/proxy/tor detection panel
│   ├── cloudflare.py    # Cloudflare/WAF panel
│   ├── speed.py         # Speed test and ping panel
│   └── security.py      # Security audit and scoring panel
├── utils/
│   ├── network.py       # ICMP ping, DNS resolution, local IP
│   ├── geo.py           # Geolocation with parallel API fallback
│   └── helpers.py       # Small utilities
└── tests/
    └── test_basic.py    # Smoke tests
```

## Notes

- **Ping**: On Linux/macOS the app tries raw ICMP sockets first. If that fails (permissions), it falls back to the system `ping` command. On Windows it always uses system ping unless run as Administrator.
- **WebRTC leak**: Full browser-based WebRTC detection isn't possible from Python. The app uses API-based checks as a reasonable proxy.
- **VPN ranges**: The datacenter IP list is fetched from a remote source and checked against the first 5000 entries for speed. If you need comprehensive checks, consider downloading a local copy.
- **Cache**: A `cache.db` file is created in the working directory. It stores results with a 5-minute TTL to avoid redundant API calls.

## License

MIT
 
