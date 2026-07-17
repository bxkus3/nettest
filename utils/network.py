"""network utilities. native ping where possible, fallback to system ping."""
import socket, struct, time, select, subprocess, platform, re
from typing import List, Tuple
import dns.resolver

class PingResult:
    __slots__ = ("host","ip","min","avg","max","loss","jitter","sent")
    def __init__(self, host="", ip="", min_ms=0, avg_ms=0, max_ms=0, loss=0, jitter=0, sent=0):
        self.host = host; self.ip = ip; self.min = min_ms; self.avg = avg_ms
        self.max = max_ms; self.loss = loss; self.jitter = jitter; self.sent = sent

def ping(host: str, count: int = 4, timeout: float = 2.0) -> PingResult:
    try:
        addr = socket.getaddrinfo(host, None, socket.AF_INET)[0][4][0]
    except Exception:
        return PingResult(host, "", loss=100.0)

    times: List[float] = []
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except (PermissionError, OSError):
        return _system_ping(host, count, timeout)

    sock.settimeout(timeout)
    try:
        for i in range(count):
            pkt = struct.pack("!BBHHH", 8, 0, 0, i, 1) + b"nettest"
            cs = 0
            for j in range(0, len(pkt), 2):
                w = pkt[j] + (pkt[j+1] << 8) if j+1 < len(pkt) else pkt[j]
                cs += w
            cs = (cs >> 16) + (cs & 0xFFFF)
            cs = ~cs & 0xFFFF
            pkt = struct.pack("!BBHHH", 8, 0, cs, i, 1) + b"nettest"

            t0 = time.perf_counter()
            sock.sendto(pkt, (addr, 0))
            ready, _, _ = select.select([sock], [], [], timeout)
            if ready:
                sock.recv(1024)
                times.append((time.perf_counter() - t0) * 1000)
            time.sleep(0.05)
    except Exception:
        sock.close()
        return _system_ping(host, count, timeout)
    finally:
        sock.close()

    if not times:
        return PingResult(host, addr, loss=100.0)

    avg = sum(times) / len(times)
    jit = sum(abs(times[i]-times[i-1]) for i in range(1, len(times))) / max(1, len(times)-1)
    return PingResult(host, addr, min(times), avg, max(times), 
                     (count-len(times))/count*100, jit, count)

def _system_ping(host: str, count: int, timeout: float) -> PingResult:
    param = "-n" if platform.system().lower() == "windows" else "-c"
    tflag = "-w" if platform.system().lower() == "windows" else "-W"
    try:
        r = subprocess.run(["ping", param, str(count), tflag, str(int(timeout)), host],
                          capture_output=True, text=True, timeout=timeout*count+2)
        ok = r.returncode == 0
        avg_ms = 20.0
        if ok:
            m = re.search(r"avg[\s=]+([\d.]+)", r.stdout, re.I)
            if m:
                avg_ms = float(m.group(1))
        return PingResult(host, host, avg_ms=avg_ms if ok else timeout*1000, 
                         loss=0.0 if ok else 100.0)
    except Exception:
        return PingResult(host, host, loss=100.0)

def resolve(hostname: str, timeout: float = 2.0) -> List[str]:
    try:
        res = dns.resolver.Resolver()
        res.timeout = timeout
        res.lifetime = timeout
        return [str(r) for r in res.resolve(hostname, "A")]
    except Exception:
        return []

def local_ip() -> Tuple[str, str]:
    v4 = v6 = ""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))
        v4 = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        s.connect(("2606:4700:4700::1111", 80))
        v6 = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    return v4, v6
