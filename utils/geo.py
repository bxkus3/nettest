"""geolocation. parallel fetches with cache."""
import asyncio
from typing import Optional
from core.cache import cache
from core.engine import engine

class GeoData:
    __slots__ = ("ip","country","city","region","isp","lat","lon","type")
    def __init__(self, ip="", country="", city="", region="", isp="", lat=0.0, lon=0.0, type=""):
        self.ip = ip; self.country = country; self.city = city; self.region = region
        self.isp = isp; self.lat = lat; self.lon = lon; self.type = type
    def to_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}

async def _from_cf() -> Optional[GeoData]:
    try:
        r = await engine.httpx.get("https://1.1.1.1/cdn-cgi/trace", timeout=3.0)
        d = {}
        for line in r.text.split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                d[k] = v
        return GeoData(ip=d.get("ip",""), country=d.get("loc",""), city=d.get("city",""),
                      region=d.get("region",""), isp=d.get("colo",""),
                      type="warp" if "warp" in r.text.lower() else "")
    except Exception:
        return None

async def _from_ipapi() -> Optional[GeoData]:
    try:
        r = await engine.httpx.get("https://ipapi.co/json/", timeout=3.0)
        d = r.json()
        return GeoData(ip=d.get("ip",""), country=d.get("country_name",""), city=d.get("city",""),
                      region=d.get("region",""), isp=d.get("org",""),
                      lat=d.get("latitude",0.0), lon=d.get("longitude",0.0))
    except Exception:
        return None

async def get_geo() -> GeoData:
    cached = cache.get("geo")
    if cached:
        return GeoData(**cached)
    results = await asyncio.gather(_from_cf(), _from_ipapi(), return_exceptions=True)
    for r in results:
        if isinstance(r, GeoData) and r.ip:
            cache.set("geo", r.to_dict(), ttl=300)
            return r
    return GeoData()
