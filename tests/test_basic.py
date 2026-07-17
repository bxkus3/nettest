"""Smoke tests. Run with: python tests/test_basic.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config():
    from core.config import cfg
    assert cfg.name == "nettest"
    assert cfg.workers > 0

def test_cache():
    from core.cache import cache
    cache.set("test", {"k": "v"})
    assert cache.get("test") == {"k": "v"}

def test_logger():
    from core.logger import get_logger
    assert get_logger("test") is not None

if __name__ == "__main__":
    test_config()
    test_cache()
    test_logger()
    print("ok")
